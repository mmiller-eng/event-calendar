// extensions/models/event_calendar_cli_test.ts
import { assertEquals, assertMatch, assertRejects } from "jsr:@std/assert@1";
import {
  createModelTestContext,
  withMockedCommand,
} from "jsr:@swamp-club/swamp-testing";
import { model } from "./event_calendar_cli.ts";

type GenerateContext = Parameters<typeof model.methods.generate.execute>[1];

async function withRepoDir(fn: (repoDir: string) => Promise<void>) {
  const repoDir = await Deno.makeTempDir();
  try {
    await fn(repoDir);
  } finally {
    await Deno.remove(repoDir, { recursive: true });
  }
}

Deno.test("generate records a successful run", async () => {
  await withRepoDir(async (repoDir) => {
    await Deno.mkdir(`${repoDir}/calendars`, { recursive: true });
    await Deno.writeTextFile(
      `${repoDir}/calendars/2026-08-16.md`,
      "# Events\n\n- Earshot show\n",
    );

    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: {
        calendarBin: ".venv/bin/calendar",
        timeoutMs: 300_000,
      },
    });

    const { calls } = await withMockedCommand(
      () => ({ stdout: "calendars/2026-08-16.md\n", code: 0 }),
      async () => {
        await model.methods.generate.execute(
          {
            location: "Seattle, WA",
            calendarLengthDays: 7,
            maxCost: 25,
            eventTypes: ["music"],
            genres: ["jazz"],
          },
          context as unknown as GenerateContext,
        );
      },
    );

    assertEquals(calls.length, 1);
    assertMatch(calls[0].args.join(" "), /--location Seattle, WA/);
    assertMatch(calls[0].args.join(" "), /--max-cost 25/);
    assertMatch(calls[0].args.join(" "), /--event-type music/);
    assertMatch(calls[0].args.join(" "), /--genre jazz/);

    const written = getWrittenResources();
    assertEquals(written.length, 1);
    assertEquals(written[0].specName, "calendar-run");
    assertEquals(written[0].data.outputPath, "calendars/2026-08-16.md");
    assertEquals(written[0].data.markdown, "# Events\n\n- Earshot show\n");
    assertEquals(written[0].data.location, "Seattle, WA");
  });
});

Deno.test("generate throws and writes nothing on CLI failure", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: {
        calendarBin: ".venv/bin/calendar",
        timeoutMs: 300_000,
      },
    });

    await withMockedCommand(
      () => ({
        stdout: "",
        stderr: "Error: ANTHROPIC_API_KEY is not set.",
        code: 3,
      }),
      async () => {
        await assertRejects(
          () =>
            model.methods.generate.execute(
              { location: "Seattle, WA", calendarLengthDays: 7 },
              context as unknown as GenerateContext,
            ),
          Error,
          "ANTHROPIC_API_KEY",
        );
      },
    );

    assertEquals(getWrittenResources().length, 0);
  });
});
