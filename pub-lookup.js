const DART_VERSIONS = [
  { flutter: "2.10", dart: "2.16.0" },
  { flutter: "3.12", dart: "3.0.0" },
  { flutter: "3.16", dart: "3.2.0" },
  { flutter: "3.22", dart: "3.4.0" },
  { flutter: "3.50", dart: "3.14.0" }
];
const PACKAGE_NAME = /^[a-z][a-z0-9_]*$/;

function packageNames(pubspec) {
  const names = new Set();
  let section = "";
  for (const line of pubspec.split(/\r?\n/)) {
    const sectionMatch = line.match(/^(dependencies|dev_dependencies|dependency_overrides)\s*:\s*$/);
    if (sectionMatch) {
      section = sectionMatch[1];
      continue;
    }
    if (/^\S/.test(line) && !/^(dependencies|dev_dependencies|dependency_overrides)\s*:/.test(line)) {
      section = "";
      continue;
    }
    if (!section) continue;
    const dependency = line.match(/^\s{2}([a-z][a-z0-9_]*)\s*:/);
    if (dependency && dependency[1] !== "flutter" && dependency[1] !== "sdk") {
      names.add(dependency[1]);
    }
  }
  return [...names].filter((name) => PACKAGE_NAME.test(name));
}

function compareDartVersions(left, right) {
  const a = left.split(".").map(Number);
  const b = right.split(".").map(Number);
  for (let index = 0; index < Math.max(a.length, b.length); index += 1) {
    const difference = (a[index] || 0) - (b[index] || 0);
    if (difference) return difference;
  }
  return 0;
}

function parseSdkConstraint(constraint) {
  const lower = constraint.match(/(?:>=|\^|>)\s*(\d+\.\d+(?:\.\d+)?)/)?.[1] ?? null;
  let upper = constraint.match(/<\s*(\d+\.\d+(?:\.\d+)?)/)?.[1] ?? null;
  if (!upper && constraint.trim().startsWith("^") && lower) {
    const [major, minor, patch = 0] = lower.split(".").map(Number);
    upper = major > 0
      ? `${major + 1}.0.0`
      : minor > 0
        ? `0.${minor + 1}.0`
        : `0.0.${patch + 1}`;
  }
  return { lower, upper };
}

function getTargetDartVersion(flutterVersion) {
  let match = DART_VERSIONS[0];
  for (const release of DART_VERSIONS) {
    if (compareDartVersions(flutterVersion, release.flutter) < 0) break;
    match = release;
  }
  return match.dart;
}

async function lookupPackage(name, targetDartVersion) {
  const url = `https://pub.dev/api/packages/${encodeURIComponent(name)}`;
  let response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/vnd.pub.v2+json" },
      signal: AbortSignal.timeout(12_000)
    });
  } catch (error) {
    return {
      name,
      verified: false,
      error: `pub.dev request failed: ${error instanceof Error ? error.message : String(error)}`
    };
  }
  if (response.status === 404) {
    return { name, verified: false, error: "Package was not found on pub.dev." };
  }
  if (!response.ok) {
    return { name, verified: false, error: `pub.dev returned HTTP ${response.status}.` };
  }
  let metadata;
  try {
    metadata = await response.json();
  } catch {
    return { name, verified: false, error: "pub.dev returned invalid package metadata." };
  }
  const latest = metadata.latest;
  if (!latest || typeof latest.version !== "string") {
    return { name, verified: false, error: "pub.dev did not return latest-version metadata." };
  }
  const sdkConstraint = latest.pubspec?.environment?.sdk;
  if (typeof sdkConstraint !== "string") {
    return {
      name,
      verified: true,
      latestVersion: latest.version,
      sdkConstraint: null,
      nullSafety: "unknown",
      compatibleWithTargetDart: null,
      url: `https://pub.dev/packages/${encodeURIComponent(name)}`
    };
  }
  const { lower, upper } = parseSdkConstraint(sdkConstraint);
  const compatibleWithTargetDart = lower === null && upper === null
    ? null
    : (lower === null || compareDartVersions(targetDartVersion, lower) >= 0)
      && (upper === null || compareDartVersions(targetDartVersion, upper) < 0);
  return {
    name,
    verified: true,
    latestVersion: latest.version,
    sdkConstraint,
    nullSafety: lower !== null && compareDartVersions(lower, "2.12.0") >= 0 ? "sound-null-safe" : "needs-review",
    compatibleWithTargetDart,
    url: `https://pub.dev/packages/${encodeURIComponent(name)}`
  };
}

export async function inspectPubspecPackages(pubspec, targetVersion) {
  const names = packageNames(pubspec);
  const targetDartVersion = getTargetDartVersion(targetVersion);
  const packages = await Promise.all(names.slice(0, 50).map((name) => lookupPackage(name, targetDartVersion)));
  return {
    targetDartVersion,
    checked: packages.length,
    truncated: names.length > 50,
    packages: packages.slice(0, 50)
  };
}
