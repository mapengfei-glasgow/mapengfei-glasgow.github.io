# Android app (`android/`) — a Trusted Web Activity around the site

An installable Android shell that opens <https://mapengfei-glasgow.github.io/>
**full screen, with no browser address bar**. It is a
[TWA](https://developer.chrome.com/docs/android/trusted-web-activity/): the page
is rendered by the Chrome already on the phone, so there is nothing to keep in
sync — the app always shows the live site, including new episodes.

There is deliberately **no Java/Kotlin source**. The launcher activity is the one
shipped by Google's Android Browser Helper library and is configured entirely
through `<meta-data>` in `app/src/main/AndroidManifest.xml`.

## What the app is

| | |
|---|---|
| Application ID | `io.github.mapengfeiglasgow.englishlistening` |
| Opens | `https://mapengfei-glasgow.github.io/` |
| minSdk / targetSdk / compileSdk | 21 / 34 / 34 |
| Launcher activity | `com.google.androidbrowserhelper.trusted.LauncherActivity` |
| Dependency | `com.google.androidbrowserhelper:androidbrowserhelper:2.5.0` (pinned, see below) |
| Android Gradle Plugin / Gradle | 8.4.0 / 8.7 |
| Signing key | `~/.android-keys/english-listening.jks` (outside the repo) |
| Download | <https://bucket.r2.mapengfei.cn/apps/english-listening-1.0.apk> |

`LauncherActivity` is **not** in `androidx.browser` — that library only has
`TrustedWebActivityIntentBuilder`. The activity comes from
`androidbrowserhelper`. The meta-data key names used in the manifest were read
out of `LauncherActivityMetadata.class` in the published AAR, not from memory.

## Environment on this host

The system JDK is **Java 8**, and no modern Android Gradle Plugin accepts it, so
a JDK 17 plus the Android SDK were unpacked under `~/android-build`. Nothing
needs root and nothing was installed system-wide.

| What | Path | Size |
|---|---|---|
| JDK 17 (Temurin 17.0.20.1+1) | `/home/deepseek-harness/android-build/jdk17` | 318 MB |
| Android SDK | `/home/deepseek-harness/android-build/sdk` | 444 MB |
| Gradle 8.7 | `/home/deepseek-harness/android-build/gradle/gradle-8.7` | 143 MB |
| Downloaded archives (kept) | `/home/deepseek-harness/android-build/dl` | 445 MB |
| Built APK, kept copy | `/home/deepseek-harness/android-build/dist/` | 0.5 MB |
| Signing key + password | `~/.android-keys/english-listening.{jks}`, `password.txt` | 4 KB |
| System Java (too old, unused) | `/usr/lib/jvm/java-8-openjdk-amd64` | — |

Installed SDK packages (`sdkmanager --list_installed`):

```
build-tools;34.0.0      34.0.0   Android SDK Build-Tools 34
platform-tools          37.0.1   Android SDK Platform-Tools
platforms;android-34    3        Android SDK Platform 34
cmdline-tools/latest    (build 9862592)
```

Roughly **1.35 GB** in total. If the prefix is deleted, everything below is
reproducible with `android/toolchain-setup.sh`.

## Build it

### 0. Once per machine — fetch the toolchain

```bash
# a proxy is only needed where the BBC/HF are blocked; see ~/memory.md
export http_proxy=http://127.0.0.1:7891 https_proxy=http://127.0.0.1:7891
./android/toolchain-setup.sh                 # -> ~/android-build
# or: ./android/toolchain-setup.sh /some/other/prefix
```

It is idempotent — anything already unpacked is left alone, so it doubles as a
"is my toolchain still there?" check. Note that the Android SDK manager ignores
`http_proxy`; the script converts the proxy settings into the
`-Dhttp(s).proxyHost` JVM properties that `sdkmanager` does understand.

### 1. Build

`JAVA_HOME` must point at the JDK 17 — note the paths, this is the whole point:

```bash
export JAVA_HOME=/home/deepseek-harness/android-build/jdk17
export ANDROID_HOME=/home/deepseek-harness/android-build/sdk
export PATH="$JAVA_HOME/bin:$PATH"

cd android
/home/deepseek-harness/android-build/gradle/gradle-8.7/bin/gradle \
    --no-daemon assembleRelease
```

Maven Central, `plugins.gradle.org` and `dl.google.com` are reachable directly on
this host, so **Gradle needs no proxy** — only the SDK download did.

The signed APK lands at:

```
android/app/build/outputs/apk/release/app-release.apk
```

`ANDROID_HOME` can be replaced by `sdk.dir` in an `android/local.properties`
(gitignored). `TWA_KEYSTORE`, `TWA_KEYSTORE_PASSWORD` and `TWA_KEY_ALIAS`
override the signing defaults, which otherwise resolve to
`~/.android-keys/english-listening.jks` and its `password.txt`.

### 2. Verify it without a device

There is no phone or emulator on this host, so the APK is checked statically.
`$ANDROID_HOME` from above:

```bash
BT=$ANDROID_HOME/build-tools/34.0.0
APK=android/app/build/outputs/apk/release/app-release.apk

# signed correctly, and which certificate
$BT/apksigner verify --verbose --print-certs "$APK"

# identity, version, and — importantly — that a launcher icon exists
$BT/aapt2 dump badging "$APK" | grep -E '^package:|^launchable-activity:|^sdkVersion|^targetSdkVersion'

# the URL the app actually opens
$BT/aapt2 dump xmltree --file AndroidManifest.xml "$APK" | grep -A1 DEFAULT_URL

# 4-byte aligned (required for a release APK)
$BT/zipalign -c -v 4 "$APK"
```

Three traps worth knowing, all of which cost time here:

- **`launchable-activity` empty ⇒ no app-drawer icon.** The icon comes from a
  `MAIN` + `LAUNCHER` intent filter, which is *separate* from the
  `VIEW`/`autoVerify` one. Without it the APK installs but cannot be opened.
- **Icon files are renamed in the APK.** AGP shortens resource paths, so
  `unzip -l "$APK" | grep ic_launcher` finds nothing even when the icons are
  there. Use
  `$BT/aapt2 dump resources "$APK" | grep -A4 'mipmap/ic_launcher'`.
- **Fingerprints print in two formats.** `apksigner` gives lowercase without
  separators, the keystore/assetlinks use uppercase colon-separated. Normalise
  before comparing or a correct build looks like a mismatch.

### 3. Publish for the phone

```bash
./venv/bin/python tools/r2_upload.py \
    /home/deepseek-harness/android-build/dist/english-listening-1.0.apk \
    --key apps/english-listening-1.0.apk
```

R2 serves `.apk` as `application/vnd.android.package-archive`, so the phone hands
it straight to the package installer. Re-download and compare hashes if in doubt
— `sha256sum` of 1.0 is
`a847379c7629b1357dcd0c607260481f2d631b4d5023199643423182a5949707`.

## Why the dependency is pinned to 2.5.0

The newer releases pull in AndroidX libraries that need a newer toolchain than
JDK 17 / AGP 8.4.0 / compileSdk 34:

| version | transitive dependency | needs |
|---|---|---|
| 2.7.3 | `androidx.core:core:1.17.0` | AGP 8.9.1+, compileSdk 36 |
| 2.6.2 | `androidx.browser:browser:1.9.0-alpha04` | AGP 8.9.1+, compileSdk 36 |
| **2.5.0** | `annotation:1.1.0`, `core:1.0.2`, `browser:1.4.0` | fine with compileSdk 34 |

2.5.0 has the same `LauncherActivity` and the same meta-data keys. To move up,
raise AGP, Gradle and compileSdk together, and install the matching platform with
`toolchain-setup.sh` (edit `SDK_PACKAGES`).

Also worth remembering: `aapt2` rejects a **double hyphen inside an XML
comment** ("The string \"--\" is not permitted within comments"), so do not write
`--theme:` in a comment in `res/values/*.xml`.

## Full screen needs assetlinks.json

Chrome only drops the URL bar if it can verify that the app and the site belong
together. That is what `static/.well-known/assetlinks.json` in the site repo is:
it lists the application ID and the SHA-256 of the **signing certificate**.

```bash
keytool -list -v -keystore ~/.android-keys/english-listening.jks \
        -alias english-listening -storepass "$(cat ~/.android-keys/password.txt)" \
        | grep SHA256
```

Currently published:

```
78:D7:79:EB:80:60:9B:1F:BC:60:2A:4A:20:68:EE:7C:C7:04:70:6F:33:49:5D:E7:39:6F:47:D6:F8:A4:16:80
```

The live file can be checked the same way Chrome checks it, which is the closest
thing to an end-to-end test available without a device:

```bash
curl -sS -G \
  --data-urlencode "source.web.site=https://mapengfei-glasgow.github.io" \
  --data-urlencode "relation=delegate_permission/common.handle_all_urls" \
  https://digitalassetlinks.googleapis.com/v1/statements:list
```

It must return a statement whose `target.androidApp.packageName` is this app and
whose `sha256Fingerprint` matches. If verification fails the app still works, it
just shows a normal Custom Tab *with* a URL bar. On a phone, check with:

```bash
adb shell pm get-app-links io.github.mapengfeiglasgow.englishlistening
```

To use a different signing key, update `assetlinks.json`, wait for GitHub Pages
to redeploy, and reinstall — Android caches the verification result, so
uninstalling and reinstalling is the reliable way to re-trigger it.

## Keeping the signing key

`~/.android-keys/english-listening.jks` (600) and `password.txt` are **not** in
git and must be backed up somewhere safe. Android identifies an app by its
signing key: lose it and no update can ever be installed over the existing app
(you would have to uninstall first). It also has to stay the one named in
`assetlinks.json`, or the app loses full-screen mode.

## Shipping an update

Bump `versionCode` (and usually `versionName`) in `android/app/build.gradle`,
rebuild, upload under a new key, and install the new APK over the old one — the
same signing key means Android treats it as an update. Nothing else changes,
because the content is the live site.

## Installing on the phone

The APK is not distributed through Google Play, so Android will ask you to allow
installing unknown apps for whichever app you open it from (browser or Files).
Install, then open "English Listening". If the URL bar is visible, the assetlinks
check failed — see above.

## The site is also installable without the APK

Because `static/manifest.json` and the icons are published, the site can be added
straight from Chrome ("Add to Home screen"). That gives the same standalone,
no-address-bar experience on Android and iOS with no build at all — a useful
fallback, and it is the same manifest the TWA reads for its name, icons and
splash colour.
