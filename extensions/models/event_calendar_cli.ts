/**
 * Wraps the project's own `calendar generate` CLI (src/cli/generate.py) so
 * swamp can trigger and track calendar-generation runs. The CLI already owns
 * trusted-source fetching, LLM-based event extraction, dedup, and filtering
 * (see src/services/discovery) — this model does not duplicate that logic,
 * it only invokes and records it.
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

/** Model definition for triggering and tracking `calendar generate` runs. */
export const model = {
  type: "event-calendar-cli",
  version: "2026.08.16.1",
  globalArguments: GlobalArgsSchema,
  resources: {
    "calendar-run": {
      description: "A completed `calendar generate` run and its output",
      schema: CalendarRunSchema,
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
        const { calendarBin, timeoutMs } = context.globalArgs;

        context.logger.info(
          "Running calendar generate for {location} ({days} days)",
          { location: args.location, days: args.calendarLengthDays },
        );

        const cmd = new Deno.Command(`${context.repoDir}/${calendarBin}`, {
          args: buildGenerateCliArgs(args),
          cwd: context.repoDir,
          stdout: "piped",
          stderr: "piped",
          signal: AbortSignal.timeout(timeoutMs),
        });

        const output = await cmd.output();
        const stderr = new TextDecoder().decode(output.stderr).trim();

        if (!output.success) {
          throw new Error(
            `calendar generate failed (exit ${output.code}): ${
              stderr || "no stderr output"
            }`,
          );
        }

        const stdout = new TextDecoder().decode(output.stdout).trim();
        const outputPath = stdout.split("\n").at(-1) ?? "";
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

        const instanceName = `${slugify(args.location)}-${
          generatedAt.replace(/[:.]/g, "-")
        }`;

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
  },
};
