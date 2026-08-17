// extensions/models/event_calendar_cli_test.ts
import { assertEquals, assertMatch, assertRejects } from "jsr:@std/assert@1";
import {
  createModelTestContext,
  withMockedCommand,
} from "jsr:@swamp-club/swamp-testing";
import { model } from "./event_calendar_cli.ts";

// All methods share the same context shape, so one alias covers every call site.
type CalendarContext = Parameters<typeof model.methods.generate.execute>[1];

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
          context as unknown as CalendarContext,
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
              context as unknown as CalendarContext,
            ),
          Error,
          "ANTHROPIC_API_KEY",
        );
      },
    );

    assertEquals(getWrittenResources().length, 0);
  });
});

Deno.test("sourcesList records one resource per listed source", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({
        stdout: "Earshot\thttps://www.earshot.org/\t2026-08-03\n" +
          "Triple Door\thttps://thetripledoor.net/mainstage-calendar\t2026-08-03",
        code: 0,
      }),
      async () => {
        await model.methods.sourcesList.execute(
          {},
          context as unknown as CalendarContext,
        );
      },
    );

    const written = getWrittenResources();
    assertEquals(written.length, 2);
    assertEquals(written[0].specName, "source");
    assertEquals(written[0].name, "earshot");
    assertEquals(written[0].data.url, "https://www.earshot.org/");
    assertEquals(written[1].name, "triple-door");
  });
});

Deno.test("sourcesList writes nothing when no sources are configured", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({ stdout: "No trusted sources configured.", code: 0 }),
      async () => {
        await model.methods.sourcesList.execute(
          {},
          context as unknown as CalendarContext,
        );
      },
    );

    assertEquals(getWrittenResources().length, 0);
  });
});

Deno.test("sourcesAdd records an added source", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({
        stdout: "Added: Earshot\thttps://www.earshot.org/\t2026-08-16",
        code: 0,
      }),
      async () => {
        await model.methods.sourcesAdd.execute(
          { name: "Earshot", url: "https://www.earshot.org/" },
          context as unknown as CalendarContext,
        );
      },
    );

    const [written] = getWrittenResources();
    assertEquals(written.specName, "source-action");
    assertEquals(written.data.action, "added");
    assertEquals(written.data.name, "Earshot");
    assertEquals(written.data.url, "https://www.earshot.org/");
  });
});

Deno.test("sourcesAdd records already_exists as a non-error outcome", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({
        stdout: "Already exists: Earshot\thttps://www.earshot.org/\t2026-08-03",
        code: 4,
      }),
      async () => {
        await model.methods.sourcesAdd.execute(
          { name: "Earshot", url: "https://www.earshot.org/" },
          context as unknown as CalendarContext,
        );
      },
    );

    const [written] = getWrittenResources();
    assertEquals(written.data.action, "already_exists");
  });
});

Deno.test("sourcesAdd throws on invalid url without writing", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({ stdout: "", stderr: "Invalid --url: ...", code: 2 }),
      async () => {
        await assertRejects(
          () =>
            model.methods.sourcesAdd.execute(
              { name: "Bad", url: "not-a-url" },
              context as unknown as CalendarContext,
            ),
          Error,
          "Invalid --url",
        );
      },
    );

    assertEquals(getWrittenResources().length, 0);
  });
});

Deno.test("sourcesRemove records a removal", async () => {
  await withRepoDir(async (repoDir) => {
    const { context, getWrittenResources } = createModelTestContext({
      repoDir,
      globalArgs: { calendarBin: ".venv/bin/calendar", timeoutMs: 300_000 },
    });

    await withMockedCommand(
      () => ({ stdout: "Removed: https://www.earshot.org/", code: 0 }),
      async () => {
        await model.methods.sourcesRemove.execute(
          { url: "https://www.earshot.org/" },
          context as unknown as CalendarContext,
        );
      },
    );

    const [written] = getWrittenResources();
    assertEquals(written.specName, "source-action");
    assertEquals(written.data.action, "removed");
    assertEquals(written.data.url, "https://www.earshot.org/");
  });
});
