const SOURCES = {
  widgets: {
    title: "Flutter widget fundamentals",
    url: "https://docs.flutter.dev/ui"
  },
  nullSafety: {
    title: "Dart: Sound null safety",
    url: "https://dart.dev/null-safety"
  },
  material: {
    title: "Migrate to Material 3",
    url: "https://docs.flutter.dev/release/breaking-changes/material-3-migration"
  },
  materialLibraries: {
    title: "Migrate to standalone Material and Cupertino packages",
    url: "https://docs.flutter.dev/release/breaking-changes/material-ui-and-cupertino-ui"
  },
  buttons: {
    title: "New buttons and button themes",
    url: "https://docs.flutter.dev/release/breaking-changes/buttons"
  },
  predictiveBack: {
    title: "Android predictive back",
    url: "https://docs.flutter.dev/release/breaking-changes/android-predictive-back"
  },
  state: {
    title: "Flutter state management",
    url: "https://docs.flutter.dev/data-and-backend/state-mgmt/intro"
  },
  debugging: {
    title: "Flutter debugging",
    url: "https://docs.flutter.dev/testing/debugging"
  },
  breaking: {
    title: "Flutter breaking changes index",
    url: "https://docs.flutter.dev/release/breaking-changes"
  }
};

const ANSWERS = [
  {
    id: "widget-types",
    matches: ["stateless", "stateful"],
    text: "A StatelessWidget describes UI from its inputs and has no mutable State object of its own. A StatefulWidget has a separate State object for data that can change during the widget’s lifetime; call setState when that local state changes so Flutter rebuilds the affected UI. Choose based on whether this widget owns changing state, not on how complex it looks.",
    sources: ["widgets"]
  },
  {
    id: "null-safety",
    matches: ["null safety", "null-safety", "nullable", "sound null"],
    text: "Sound null safety distinguishes nullable and non-nullable types. A non-nullable variable cannot contain null unless you explicitly make its type nullable with ?. The analyzer and runtime can then rely on those guarantees, catching many null errors before execution. For an older app, also check the Dart SDK constraint and whether each dependency supports null safety; this answer alone cannot certify package compatibility.",
    sources: ["nullSafety"]
  },
  {
    id: "material-3",
    matches: ["material 3", "material3", "usematerial3"],
    text: "Starting with Flutter 3.16, Material 3 became the default (useMaterial3 is true). Existing apps can therefore show updated colors, typography, component styling, and defaults even when their widget code still compiles. Review screenshots and golden tests, migrate custom color schemes where needed, and use useMaterial3: false only as a temporary transition—not as a permanent migration.",
    sources: ["material"]
  },
  {
    id: "flutter-2-migration",
    matches: ["flatbutton", "raisedbutton", "willpopscope", "flutter 2.10", "flutter 2 app", "latest stable", "migration"],
    text: "A safe migration is staged; this widget sample alone cannot identify every build, dependency, Android, or app-specific change.\n\n1. Record the current Flutter/Dart versions and get the Flutter 2.10 app’s analyze and test baselines.\n2. Check the Dart SDK constraint and upgrade or replace packages that don’t support the target Dart version; verify their null-safety and Flutter compatibility individually.\n3. Migrate deprecated APIs found in the app. FlatButton maps to TextButton and RaisedButton maps to ElevatedButton. WillPopScope maps to PopScope; move the decision to canPop and handle pop notifications with the callback supported by your target SDK.\n4. For Flutter 3.50, plan the formal deprecation of the in-framework Material/Cupertino libraries: the official guide describes migrating to the standalone material_ui and cupertino_ui packages and notes compatibility limitations with dependencies that expose old SDK types.\n5. Review Material 3 visual changes (default since Flutter 3.16), Android build-tool/target-SDK requirements for the chosen Flutter release, and package-specific migration guides.\n6. Run flutter analyze, widget tests, and device checks on the target SDK. Do not treat this partial API map as a complete migration checklist.",
    sources: ["buttons", "predictiveBack", "material", "materialLibraries", "breaking"]
  },
  {
    id: "state-management",
    matches: ["provider", "riverpod", "state management", "app-wide state"],
    text: "Flutter’s official state-management guide explains app state concepts and common approaches, but it does not provide a version-aware, authoritative Provider-versus-Riverpod comparison. Provider and Riverpod are separate packages, so compare their current package documentation and compatibility with your Dart/Flutter target before choosing. If you share your state and testing requirements, I can help frame that comparison without presenting it as Flutter framework guidance.",
    sources: ["state"]
  },
  {
    id: "crash",
    matches: ["crash", "crashes", "crashing", "shop owner's phone", "shop owners phone"],
    text: "There isn’t enough evidence to identify the cause yet. Please share the device model and Android version, the exact reproduction steps, the first relevant exception/stack trace from flutter run or device logs, and whether the same build works on another device. Redact customer data and secrets. With that evidence, we can trace the failure instead of guessing.",
    sources: ["debugging"]
  }
];

const MIGRATIONS = [
  {
    id: "flat-button",
    pattern: /\bFlatButton\b/,
    title: "FlatButton",
    replacement: "TextButton",
    version: "Replacement available before Flutter 2.10",
    details: "The official migration guide maps FlatButton to TextButton. The current guide does not state the exact first release for this replacement; review ButtonStyle changes if the old widget had custom styling.",
    source: "buttons",
    minTarget: "2.10"
  },
  {
    id: "raised-button",
    pattern: /\bRaisedButton\b/,
    title: "RaisedButton",
    replacement: "ElevatedButton",
    version: "Replacement available before Flutter 2.10",
    details: "The official migration guide maps RaisedButton to ElevatedButton. The current guide does not state the exact first release for this replacement; review ButtonStyle changes if the old widget had custom styling.",
    source: "buttons",
    minTarget: "2.10"
  },
  {
    id: "outline-button",
    pattern: /\bOutlineButton\b/,
    title: "OutlineButton",
    replacement: "OutlinedButton",
    version: "Replacement available before Flutter 2.10",
    details: "The official migration guide maps OutlineButton to OutlinedButton. The current guide does not state the exact first release for this replacement.",
    source: "buttons",
    minTarget: "2.10"
  },
  {
    id: "button-theme",
    pattern: /\bButtonTheme\b/,
    title: "ButtonTheme",
    replacement: "TextButtonTheme / ElevatedButtonTheme / OutlinedButtonTheme",
    version: "New button API available before Flutter 2.10",
    details: "Choose the corresponding component theme. ButtonStyle replaces many of the old individual styling properties; check the migration guide for custom visuals.",
    source: "buttons",
    minTarget: "2.10"
  },
  {
    id: "will-pop-scope",
    pattern: /\bWillPopScope\b/,
    title: "WillPopScope",
    replacement: "PopScope",
    version: "Deprecated after Flutter 3.12.0-1.0.pre",
    details: "Move the pop decision ahead of the gesture with canPop. The notification callback runs after the pop is handled, so it is not a drop-in async veto callback.",
    source: "predictiveBack",
    minTarget: "3.12"
  },
  {
    id: "material-3-default",
    pattern: /\buseMaterial3\s*:\s*true\b/,
    title: "Material 3 default",
    replacement: "Review ThemeData colors and component visuals",
    version: "Default changed in Flutter 3.16",
    details: "Material 3 is enabled by default from Flutter 3.16. Explicit opt-in is redundant on newer SDKs, but review this app’s theme and visual tests rather than deleting the setting blindly.",
    source: "material",
    minTarget: "3.16"
  },
  {
    id: "material-library-import",
    pattern: /package:flutter\/(?:material|cupertino)\.dart/,
    title: "In-framework Material/Cupertino library",
    replacement: "material_ui / cupertino_ui standalone packages",
    version: "Packages available 3.47; framework libraries deprecated in 3.50",
    details: "The Flutter 3.50 migration guide describes the standalone packages and a dart fix migration. Check third-party packages for API signatures that still expose Flutter SDK design types; the compatibility bridge cannot resolve those type mismatches.",
    source: "materialLibraries",
    minTarget: "3.50"
  }
];

const compareVersions = (left, right) => {
  const a = left.split(".").map(Number);
  const b = right.split(".").map(Number);
  for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
    const difference = (a[i] || 0) - (b[i] || 0);
    if (difference) return difference;
  }
  return 0;
};

export function getAnswer(question, targetVersion) {
  const normalized = question.toLowerCase();
  const answer = ANSWERS.find((item) => item.matches.some((match) => normalized.includes(match)));
  if (!answer) {
    return {
      text: "I don’t have a sufficiently grounded answer for that question in the indexed official Flutter/Dart sources. Try asking about widgets, null safety, Material 3, a known API migration, or share a crash log. I won’t guess or invent a citation.",
      sources: ["breaking"]
    };
  }
  let text = answer.text;
  if (answer.id === "material-3" && compareVersions(targetVersion, "3.16") < 0) {
    text = "Material 3 became the default in Flutter 3.16, which is newer than your selected target. On a target before 3.16, Material 3 is not the default; check the migration guide if you opt in explicitly.\n\n" + text;
  }
  return { text, sources: answer.sources };
}

export function findMigrations(pubspec, widgetCode, fromVersion, toVersion) {
  const combined = `${pubspec}\n${widgetCode}`;
  const found = MIGRATIONS.filter((migration) => migration.pattern.test(combined))
    .filter((migration) => compareVersions(toVersion, migration.minTarget) >= 0)
    .map((migration) => ({ ...migration }));
  const sdkMatch = pubspec.match(/^\s*sdk\s*:\s*['"]?([^'"\r\n]+)['"]?/m);
  const findings = found.map((item) => ({ ...item, category: "api" }));
  if (sdkMatch && /<\s*3(?:\.0)?(?:\.0)?\b/.test(sdkMatch[1]) && compareVersions(toVersion, "3.0") >= 0) {
    findings.unshift({
      id: "dart-sdk-constraint",
      title: "Dart SDK constraint",
      replacement: "Review the environment.sdk range for the target Flutter release",
      version: "Dart 3 requires a compatible SDK constraint",
      details: `The manifest has an SDK constraint of “${sdkMatch[1].trim()}”. Confirm the Dart version bundled with your target Flutter SDK, then update the constraint only after checking all dependencies for compatibility.`,
      source: "nullSafety",
      category: "sdk"
    });
  }
  const dependencyNames = [...pubspec.matchAll(/^\s{2}([a-zA-Z0-9_]+)\s*:/gm)]
    .map((match) => match[1])
    .filter((name) => name !== "sdk" && name !== "flutter");
  if (dependencyNames.length) {
    findings.push({
      id: "package-compatibility",
      title: "Dependency compatibility needs verification",
      replacement: [...new Set(dependencyNames)].join(", "),
      version: "Check each package against the target",
      details: "A pubspec alone cannot prove null-safety or target-SDK compatibility. Check each package’s current pub.dev page and changelog, then resolve constraints before API migration.",
      source: "breaking",
      category: "dependency"
    });
  }
  return findings;
}

function renderCitations(container, sourceIds) {
  container.replaceChildren();
  [...new Set(sourceIds)].forEach((id) => {
    const source = SOURCES[id];
    if (!source) return;
    const link = document.createElement("a");
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = `${source.title} ↗`;
    container.append(link);
  });
}

function renderAnswer(result, targetVersion) {
  const card = document.querySelector("#answer-card");
  const body = document.querySelector("#answer-body");
  const paragraphs = result.text.split(/\n{2,}/);
  body.replaceChildren();
  paragraphs.forEach((text) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    body.append(paragraph);
  });
  document.querySelector("#answer-version").textContent = `Answer · Flutter ${targetVersion}`;
  renderCitations(document.querySelector("#answer-citations"), result.sources);
  card.classList.remove("hidden");
  card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderMigrations(findings, toVersion) {
  const result = document.querySelector("#map-results");
  const list = document.querySelector("#migration-list");
  list.replaceChildren();
  document.querySelector("#map-result-title").textContent = findings.length
    ? `Review ${findings.length} migration ${findings.length === 1 ? "item" : "items"}`
    : "No known changes detected";
  document.querySelector("#results-count").textContent = `${findings.length} ${findings.length === 1 ? "finding" : "findings"}`;
  if (!findings.length) {
    const empty = document.createElement("li");
    empty.className = "empty-result";
    empty.textContent = "No APIs from the current migration map were found in the supplied text. This does not confirm that the app is compatible; inspect analyzer output, package release notes, and the complete breaking-changes index.";
    list.append(empty);
  }
  findings.forEach((finding, index) => {
    const item = document.createElement("li");
    item.className = "migration-item";
    const number = document.createElement("span");
    number.className = "migration-number";
    number.textContent = String(index + 1).padStart(2, "0");
    const content = document.createElement("div");
    content.className = "migration-content";
    const title = document.createElement("div");
    title.className = "migration-title";
    const label = document.createElement("strong");
    label.textContent = finding.title;
    const version = document.createElement("span");
    version.className = "version-tag";
    version.textContent = finding.version;
    title.append(label, version);
    const replacement = document.createElement("span");
    replacement.className = "replacement";
    replacement.textContent = `→ ${finding.replacement}`;
    const details = document.createElement("p");
    details.textContent = finding.details;
    const source = SOURCES[finding.source];
    const link = document.createElement("a");
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = `Read ${source.title} ↗`;
    content.append(title, replacement, details, link);
    item.append(number, content);
    list.append(item);
  });
  result.dataset.targetVersion = toVersion;
  result.classList.remove("hidden");
}

function switchView(viewName) {
  const isMigration = viewName === "migration";
  document.querySelector("#mentor-view").classList.toggle("hidden", isMigration);
  document.querySelector("#migration-view").classList.toggle("hidden", !isMigration);
  document.querySelector("#breadcrumb-view").textContent = isMigration ? "Migration map" : "Mentor";
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
}

function startApp() {
  const askButton = document.querySelector("#ask-button");
  const questionInput = document.querySelector("#question-input");
  askButton.addEventListener("click", () => {
    const question = questionInput.value.trim();
    if (!question) {
      questionInput.focus();
      return;
    }
    renderAnswer(getAnswer(question, document.querySelector("#target-version").value), document.querySelector("#target-version").value);
  });
  questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askButton.click();
    }
  });
  document.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      questionInput.value = button.dataset.question;
      if (button.classList.contains("recent-question")) {
        switchView("mentor");
        askButton.click();
      } else {
        questionInput.focus();
      }
    });
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  document.querySelector("[data-open-view='migration']").addEventListener("click", () => switchView("migration"));
  document.querySelector("#clear-answer").addEventListener("click", () => {
    document.querySelector("#answer-card").classList.add("hidden");
  });
  document.querySelector("#map-button").addEventListener("click", () => {
    const findings = findMigrations(
      document.querySelector("#pubspec-input").value,
      document.querySelector("#widget-input").value,
      document.querySelector("#map-from-version").value,
      document.querySelector("#map-to-version").value
    );
    renderMigrations(findings, document.querySelector("#map-to-version").value);
  });
}

if (typeof document !== "undefined") startApp();
