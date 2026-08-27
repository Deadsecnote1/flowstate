import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  computeDAGLayout,
  useHostTheme,
} from "cursor/canvas";

const LAYERS = [
  { id: "entry", label: "Entry", detail: "todo / __main__" },
  { id: "app", label: "Application", detail: "TodoApplication" },
  { id: "window", label: "Window shell", detail: "TodoWindow + ViewStack" },
  { id: "tasks", label: "Tasks UI", detail: "list + TodoRow" },
  { id: "planner", label: "Planner UI", detail: "timeline + TaskEditor" },
  { id: "clock", label: "Clock UI", detail: "Timer + Stopwatch" },
  { id: "todoStore", label: "TodoStore", detail: "todos.json" },
  { id: "planStore", label: "PlannerStore", detail: "planner.json" },
  { id: "xdg", label: "XDG data dir", detail: "~/.local/share/…" },
];

const EDGES = [
  { from: "entry", to: "app" },
  { from: "app", to: "window" },
  { from: "window", to: "tasks" },
  { from: "window", to: "planner" },
  { from: "window", to: "clock" },
  { from: "tasks", to: "todoStore" },
  { from: "planner", to: "planStore" },
  { from: "todoStore", to: "xdg" },
  { from: "planStore", to: "xdg" },
];

function ArchitectureDag() {
  const theme = useHostTheme();
  const layout = computeDAGLayout({
    nodes: LAYERS.map((n) => ({ id: n.id })),
    edges: EDGES,
    direction: "vertical",
    nodeWidth: 150,
    nodeHeight: 44,
    rankGap: 36,
    nodeGap: 28,
    padding: 12,
  });
  const byId = Object.fromEntries(LAYERS.map((n) => [n.id, n]));

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      style={{ display: "block", maxWidth: 720 }}
    >
      {layout.edges.map((e, i) => (
        <line
          key={i}
          x1={e.sourceX}
          y1={e.sourceY}
          x2={e.targetX}
          y2={e.targetY}
          stroke={theme.stroke.secondary}
          strokeWidth={1.5}
        />
      ))}
      {layout.nodes.map((n) => {
        const meta = byId[n.id];
        const isStore = n.id.includes("Store") || n.id === "xdg";
        return (
          <g key={n.id}>
            <rect
              x={n.x}
              y={n.y}
              width={150}
              height={44}
              rx={6}
              fill={isStore ? theme.fill.tertiary : theme.fill.secondary}
              stroke={
                n.id === "window" ? theme.accent.primary : theme.stroke.tertiary
              }
              strokeWidth={n.id === "window" ? 1.5 : 1}
            />
            <text
              x={n.x + 75}
              y={n.y + 18}
              textAnchor="middle"
              fill={theme.text.primary}
              fontSize={12}
              fontWeight={600}
            >
              {meta.label}
            </text>
            <text
              x={n.x + 75}
              y={n.y + 34}
              textAnchor="middle"
              fill={theme.text.tertiary}
              fontSize={10}
            >
              {meta.detail}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export default function TodoArchitecture() {
  const theme = useHostTheme();

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>Todo app architecture</H1>
        <Text tone="secondary">
          Design of the GTK4 / libadwaita desktop app: layered UI, dual
          persistence stores, and Debian packaging. Source: project tree under{" "}
          <Code>src/todo/</Code>.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="3" label="Primary views" />
        <Stat value="2" label="JSON stores" />
        <Stat value="GTK4 + Adw" label="UI toolkit" />
        <Stat value="Meson / deb" label="Packaging" />
      </Grid>

      <Callout tone="info" title="Core idea">
        One Adw.Application owns a single window. The window is a ViewStack of
        independent feature pages (Tasks, Planner, Clock). Each feature that
        needs persistence talks to its own store; stores write XDG JSON and
        notify subscribers so the UI refreshes without a global event bus.
      </Callout>

      <Stack gap={8}>
        <H2>Runtime layering</H2>
        <Text tone="secondary">
          Top-down control flow. Accent border marks the window shell that
          composes feature pages.
        </Text>
        <Card>
          <CardBody>
            <ArchitectureDag />
          </CardBody>
        </Card>
      </Stack>

      <Stack gap={8}>
        <H2>Module map</H2>
        <Table
          headers={["Module", "Role", "Depends on"]}
          rows={[
            [
              "main.py",
              "GApplication lifecycle, About, Preferences actions",
              "Adw, TodoWindow",
            ],
            [
              "window.py",
              "Header ViewSwitcher, Tasks page, CSS, toast overlay",
              "store, planner, clock, row",
            ],
            [
              "store.py",
              "TodoItem CRUD, filters, XDG todos.json",
              "GLib paths",
            ],
            [
              "row.py",
              "List row: toggle, edit, delete signals",
              "Gtk, TodoItem",
            ],
            [
              "planner.py",
              "Inbox + week strip + timeline + TaskEditor panel",
              "planner_store",
            ],
            [
              "planner_store.py",
              "PlanTask model, daily repeat expansion, planner.json",
              "GLib paths",
            ],
            [
              "clock.py",
              "Timer / Stopwatch; Cairo ClockDigits for huge readout",
              "GLib timeouts, cairo",
            ],
            [
              "preferences.py",
              "Adw preferences dialog (GSettings when schema present)",
              "Adw",
            ],
          ]}
        />
      </Stack>

      <Divider />

      <H2>Feature architecture</H2>
      <Grid columns={3} gap={16}>
        <Card>
          <CardHeader>Tasks</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                Classic list UX: entry field, All / Active / Done filters,
                search bar, toast feedback.
              </Text>
              <Text tone="secondary">
                <Code>TodoStore</Code> holds items in memory, persists on every
                mutation, and fans out via <Code>subscribe()</Code> so{" "}
                <Code>refresh()</Code> rebuilds rows.
              </Text>
              <Row gap={6}>
                <Pill tone="neutral">TodoItem</Pill>
                <Pill tone="neutral">TodoRow</Pill>
                <Pill tone="neutral">todos.json</Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader trailing={<Pill tone="info">Structured-inspired</Pill>}>
            Planner
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                Three-pane layout: Inbox (left), day timeline (center), coral
                TaskEditor panel (right).
              </Text>
              <Text tone="secondary">
                <Code>PlannerStore.tasks_for_day()</Code> merges dated tasks
                with <Code>repeat=daily</Code> virtual instances. Editor emits
                saved / deleted / closed; the page owns store writes.
              </Text>
              <Row gap={6}>
                <Pill tone="neutral">PlanTask</Pill>
                <Pill tone="neutral">TaskEditor</Pill>
                <Pill tone="neutral">planner.json</Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Clock</CardHeader>
          <CardBody>
            <Stack gap={8}>
              <Text>
                Nested ViewStack: Timer (countdown + dynamic presets) and
                Stopwatch (laps).
              </Text>
              <Text tone="secondary">
                Digits are drawn with Cairo (<Code>ClockDigits</Code>) so size
                is theme-independent. GLib timeouts drive ticks; finished timer
                raises a toast + notification via the window.
              </Text>
              <Row gap={6}>
                <Pill tone="neutral">TimerView</Pill>
                <Pill tone="neutral">StopwatchView</Pill>
                <Pill tone="neutral">no disk I/O</Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <Stack gap={8}>
        <H2>Data & state</H2>
        <Grid columns={2} gap={16}>
          <Stack gap={10}>
            <H3>Persistence</H3>
            <Text>
              Both stores use{" "}
              <Code>~/.local/share/io.github.thanushiyan.Todo/</Code>:
            </Text>
            <Table
              headers={["File", "Contents"]}
              rows={[
                ["todos.json", "items[] — id, title, completed, notes, created_at"],
                [
                  "planner.json",
                  "tasks[] + inbox[] — schedule, duration, repeat, color",
                ],
              ]}
            />
            <Text tone="secondary">
              No database. JSON keeps the Debian package architecture-all and
              easy to inspect. Writes are synchronous after each mutation
              (acceptable for local desktop scale).
            </Text>
          </Stack>
          <Stack gap={10}>
            <H3>UI update pattern</H3>
            <Text>
              Observer, not Redux: stores keep a listener list; pages call{" "}
              <Code>subscribe(refresh)</Code> once. Mutations{" "}
              <Code>save()</Code> then <Code>_notify()</Code>.
            </Text>
            <Text tone="secondary">
              List UIs rebuild children on refresh (simple, predictable). Clock
              keeps ephemeral state only in the widgets. GApplication single
              instance prevents duplicate windows for the same app id.
            </Text>
            <Callout tone="neutral" title="Why split stores?">
              Todo list and day planner have different schemas and query
              patterns. Separate files avoid coupling and let either feature
              evolve without migrations on the other.
            </Callout>
          </Stack>
        </Grid>
      </Stack>

      <CollapsibleSection title="Design decisions" defaultOpen>
        <Stack gap={12}>
          <Stack gap={4}>
            <Text weight="semibold">GTK4 + libadwaita</Text>
            <Text tone="secondary">
              Native Debian/GNOME look, system dark/light, keyboard shortcuts,
              and .desktop / AppStream integration. Python GI keeps the codebase
              small versus C/Rust for a personal utility.
            </Text>
          </Stack>
          <Stack gap={4}>
            <Text weight="semibold">ViewStack navigation</Text>
            <Text tone="secondary">
              Tasks / Planner / Clock share one window and header. Feature pages
              stay isolated modules; the shell only wires actions, CSS, and
              toasts.
            </Text>
          </Stack>
          <Stack gap={4}>
            <Text weight="semibold">Cairo clock digits</Text>
            <Text tone="secondary">
              Theme CSS and Pango markup failed to force large type on Mint. A
              DrawingArea sizes glyphs to ~78% of allocated height so Timer and
              Stopwatch always read as the visual focus.
            </Text>
          </Stack>
          <Stack gap={4}>
            <Text weight="semibold">Planner visual language</Text>
            <Text tone="secondary">
              Planner CSS uses a Structured-inspired dark surface and coral
              accent (#E8837A) scoped to planner-* classes, without forcing the
              whole app into that theme.
            </Text>
          </Stack>
        </Stack>
      </CollapsibleSection>

      <CollapsibleSection title="Packaging & desktop integration" defaultOpen={false}>
        <Stack gap={10}>
          <Text>
            Build with Meson + Debian packaging so users get a{" "}
            <Code>.deb</Code> and a menu entry.
          </Text>
          <Table
            headers={["Artifact", "Purpose"]}
            rows={[
              ["meson.build / todo.in", "Install binary + Python package"],
              ["data/*.desktop", "App menu launcher + Icon name"],
              ["data/*.metainfo.xml", "AppStream / Software store metadata"],
              ["data/*.gschema.xml", "Optional GSettings keys"],
              ["data/icons/hicolor/**", "SVG + PNG sizes for Cinnamon/Mint"],
              ["debian/*", "dpkg-buildpackage → todo_*.deb"],
              ["install-local.sh", "User-local .desktop + icons without sudo"],
            ]}
          />
          <Text tone="secondary">
            App id <Code>io.github.thanushiyan.Todo</Code> ties D-Bus uniqueness,
            icons, schemas, and XDG paths together.
          </Text>
        </Stack>
      </CollapsibleSection>

      <Spacer height={8} />
      <Text tone="tertiary">
        Generated from the current codebase layout — not a formal RFC.
      </Text>
    </Stack>
  );
}
