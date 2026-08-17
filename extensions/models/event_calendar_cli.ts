/**
 * Wraps the project's own `calendar` CLI (src/cli/generate.py, src/cli/sources.py)
 * so swamp can trigger and track calendar-generation runs and trusted-source
 * management. The CLI already owns discovery, LLM-based event extraction,
 * dedup/filtering, and the trusted-source store (see src/services/discovery)
 * — this model does not duplicate that logic, it only invokes and records it.
 *
 * @module
 */
// extensions/models/event_calendar_cli.ts
import { z } from "npm:zod@4";

const GlobalArgsSchema = z.object({
  calendarBin: z.string().default(".venv/bin/calendar"),
  // Discovery fetches + LLM-extracts each trusted source sequentially (see
  // src/services/discovery/__init__.py), so 15+ sources can take minutes.
  timeoutMs: z.number().int().positive().default(900_000),
});

type GlobalArgs = z.infer<typeof GlobalArgsSchema>;

const GenerateArgsSchema = z.object({
  location: z.string(),
  calendarLengthDays: z.number().int().positive(),
  maxCost: z.number().nonnegative().optional(),
  eventTypes: z.array(z.string()).optional(),
  genres: z.array(z.string()).optional(),
  startAfter: z.string().regex(/^\d{2}:\d{2}$/).optional(),
  startBefore: z.string().regex(/^\d{2}:\d{2}$/).optional(),
  output: z.string().optional(),
  model: z.string().optional(),
});

type GenerateArgs = z.infer<typeof GenerateArgsSchema>;

const SourcesAddArgsSchema = z.object({
  name: z.string(),
  url: z.string(),
});

type SourcesAddArgs = z.infer<typeof SourcesAddArgsSchema>;

const SourcesRemoveArgsSchema = z.object({
  url: z.string(),
});

type SourcesRemoveArgs = z.infer<typeof SourcesRemoveArgsSchema>;

const CalendarRunSchema = z.object({
  location: z.string(),
  calendarLengthDays: z.number(),
  maxCost: z.number().optional(),
  eventTypes: z.array(z.string()).optional(),
  genres: z.array(z.string()).optional(),
  startAfter: z.string().optional(),
  startBefore: z.string().optional(),
  model: z.string().optional(),
  outputPath: z.string(),
  markdown: z.string(),
  generatedAt: z.iso.datetime(),
});

const SourceSchema = z.object({
  name: z.string(),
  url: z.string(),
  addedAt: z.string(),
  listedAt: z.iso.datetime(),
});

const SourceActionSchema = z.object({
  url: z.string(),
  action: z.enum(["added", "already_exists", "removed"]),
  name: z.string().optional(),
  addedAt: z.string().optional(),
  performedAt: z.iso.datetime(),
});

type MethodContext = {
  globalArgs: GlobalArgs;
  repoDir: string;
  logger: {
    info: (msg: string, ...args: unknown[]) => void;
  };
  writeResource: (
    specName: string,
    name: string,
    data: Record<string, unknown>,
  ) => Promise<{ name: string }>;
};

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function timestampSuffix(): string {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

async function runCalendarCli(
  cliArgs: string[],
  context: { globalArgs: GlobalArgs; repoDir: string },
): Promise<{ success: boolean; code: number; stdout: string; stderr: string }> {
  const { calendarBin, timeoutMs } = context.globalArgs;

  const cmd = new Deno.Command(`${context.repoDir}/${calendarBin}`, {
    args: cliArgs,
    cwd: context.repoDir,
    stdout: "piped",
    stderr: "piped",
    signal: AbortSignal.timeout(timeoutMs),
  });

  const output = await cmd.output();
  return {
    success: output.success,
    code: output.code,
    stdout: new TextDecoder().decode(output.stdout).trim(),
    stderr: new TextDecoder().decode(output.stderr).trim(),
  };
}

function buildGenerateCliArgs(args: GenerateArgs): string[] {
  const cliArgs = [
    "generate",
    "--location",
    args.location,
    "--calendar-length-days",
    String(args.calendarLengthDays),
  ];

  if (args.maxCost !== undefined) {
    cliArgs.push("--max-cost", String(args.maxCost));
  }
  for (const eventType of args.eventTypes ?? []) {
    cliArgs.push("--event-type", eventType);
  }
  for (const genre of args.genres ?? []) {
    cliArgs.push("--genre", genre);
  }
  if (args.startAfter !== undefined) {
    cliArgs.push("--start-after", args.startAfter);
  }
  if (args.startBefore !== undefined) {
    cliArgs.push("--start-before", args.startBefore);
  }
  if (args.output !== undefined) {
    cliArgs.push("--output", args.output);
  }
  if (args.model !== undefined) {
    cliArgs.push("--model", args.model);
  }

  return cliArgs;
}

/** Parses a `name\turl\taddedAt` line from `calendar sources list`. */
function parseSourceLine(
  line: string,
): { name: string; url: string; addedAt: string } {
  const [name, url, addedAt] = line.split("\t");
  if (!name || !url || !addedAt) {
    throw new Error(`Unrecognized "calendar sources list" line: ${line}`);
  }
  return { name, url, addedAt };
}

/** Strips a known `calendar sources add` status prefix and parses the rest. */
function parseSourceStatusLine(
  prefix: string,
  line: string,
): { name: string; url: string; addedAt: string } {
  if (!line.startsWith(prefix)) {
    throw new Error(
      `Unrecognized "calendar sources add" output: ${line}`,
    );
  }
  return parseSourceLine(line.slice(prefix.length));
}

/** Model definition for triggering and tracking `calendar` CLI runs. */
export const model = {
  type: "event-calendar-cli",
  version: "2026.08.16.2",
  globalArguments: GlobalArgsSchema,
  upgrades: [
    {
      toVersion: "2026.08.16.2",
      description:
        "Add sourcesAdd/sourcesList/sourcesRemove methods and source/source-action resources; no globalArguments change",
      upgradeAttributes: (old: Record<string, unknown>) => old,
    },
  ],
  resources: {
    "calendar-run": {
      description: "A completed `calendar generate` run and its output",
      schema: CalendarRunSchema,
      lifetime: "infinite",
      garbageCollection: 20,
    },
    "source": {
      description: "A trusted source as of the last `calendar sources list`",
      schema: SourceSchema,
      lifetime: "infinite",
      garbageCollection: 10,
    },
    "source-action": {
      description: "A `calendar sources add`/`remove` call and its result",
      schema: SourceActionSchema,
      lifetime: "infinite",
      garbageCollection: 20,
    },
  },
  methods: {
    generate: {
      description:
        "Run `calendar generate` with the given preferences and record its output",
      arguments: GenerateArgsSchema,
      execute: async (args: GenerateArgs, context: MethodContext) => {
        context.logger.info(
          "Running calendar generate for {location} ({days} days)",
          { location: args.location, days: args.calendarLengthDays },
        );

        const result = await runCalendarCli(buildGenerateCliArgs(args), context);

        if (!result.success) {
          throw new Error(
            `calendar generate failed (exit ${result.code}): ${
              result.stderr || "no stderr output"
            }`,
          );
        }

        const outputPath = result.stdout.split("\n").at(-1) ?? "";
        if (!outputPath) {
          throw new Error(
            "calendar generate succeeded but printed no output path",
          );
        }

        const absoluteOutputPath = outputPath.startsWith("/")
          ? outputPath
          : `${context.repoDir}/${outputPath}`;
        const markdown = await Deno.readTextFile(absoluteOutputPath);
        const generatedAt = new Date().toISOString();
        const instanceName = `${slugify(args.location)}-${timestampSuffix()}`;

        context.logger.info(
          "calendar generate wrote {outputPath} ({bytes} bytes)",
          { outputPath, bytes: markdown.length },
        );

        const handle = await context.writeResource("calendar-run", instanceName, {
          location: args.location,
          calendarLengthDays: args.calendarLengthDays,
          maxCost: args.maxCost,
          eventTypes: args.eventTypes,
          genres: args.genres,
          startAfter: args.startAfter,
          startBefore: args.startBefore,
          model: args.model,
          outputPath,
          markdown,
          generatedAt,
        });

        return { dataHandles: [handle] };
      },
    },
    sourcesList: {
      description:
        "Run `calendar sources list` and record the current trusted-source set",
      arguments: z.object({}),
      execute: async (_args: Record<string, never>, context: MethodContext) => {
        context.logger.info("Running calendar sources list", {});

        const result = await runCalendarCli(["sources", "list"], context);
        if (!result.success) {
          throw new Error(
            `calendar sources list failed (exit ${result.code}): ${
              result.stderr || "no stderr output"
            }`,
          );
        }

        if (result.stdout === "No trusted sources configured.") {
          context.logger.info("No trusted sources configured", {});
          return { dataHandles: [] };
        }

        const listedAt = new Date().toISOString();
        const handles: Array<{ name: string }> = [];
        for (const line of result.stdout.split("\n")) {
          const source = parseSourceLine(line);
          const handle = await context.writeResource(
            "source",
            slugify(source.name),
            { ...source, listedAt },
          );
          handles.push(handle);
        }

        context.logger.info("Listed {count} trusted sources", {
          count: handles.length,
        });

        return { dataHandles: handles };
      },
    },
    sourcesAdd: {
      description: "Run `calendar sources add` and record the result",
      arguments: SourcesAddArgsSchema,
      execute: async (args: SourcesAddArgs, context: MethodContext) => {
        context.logger.info("Running calendar sources add for {name}", {
          name: args.name,
        });

        const result = await runCalendarCli(
          ["sources", "add", "--name", args.name, "--url", args.url],
          context,
        );

        // Exit 4 means "already exists" — an idempotent no-op, not a failure
        // (see src/cli/sources.py add_source).
        if (!result.success && result.code !== 4) {
          throw new Error(
            `calendar sources add failed (exit ${result.code}): ${
              result.stderr || "no stderr output"
            }`,
          );
        }

        const parsed = result.code === 4
          ? parseSourceStatusLine("Already exists: ", result.stdout)
          : parseSourceStatusLine("Added: ", result.stdout);
        const performedAt = new Date().toISOString();
        const instanceName = `${slugify(args.url)}-${timestampSuffix()}`;

        context.logger.info("calendar sources add: {action} {name}", {
          action: result.code === 4 ? "already_exists" : "added",
          name: parsed.name,
        });

        const handle = await context.writeResource("source-action", instanceName, {
          url: parsed.url,
          action: result.code === 4 ? "already_exists" : "added",
          name: parsed.name,
          addedAt: parsed.addedAt,
          performedAt,
        });

        return { dataHandles: [handle] };
      },
    },
    sourcesRemove: {
      description: "Run `calendar sources remove` and record the result",
      arguments: SourcesRemoveArgsSchema,
      execute: async (args: SourcesRemoveArgs, context: MethodContext) => {
        context.logger.info("Running calendar sources remove for {url}", {
          url: args.url,
        });

        const result = await runCalendarCli(
          ["sources", "remove", "--url", args.url],
          context,
        );

        if (!result.success) {
          throw new Error(
            `calendar sources remove failed (exit ${result.code}): ${
              result.stderr || "no stderr output"
            }`,
          );
        }

        const performedAt = new Date().toISOString();
        const instanceName = `${slugify(args.url)}-${timestampSuffix()}`;

        context.logger.info("calendar sources remove: removed {url}", {
          url: args.url,
        });

        const handle = await context.writeResource("source-action", instanceName, {
          url: args.url,
          action: "removed",
          performedAt,
        });

        return { dataHandles: [handle] };
      },
    },
  },
};
