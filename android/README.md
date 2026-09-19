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
| minSdk / targetSdk | 21 / 34 |
| Launcher activity | `com.google.androidbrowserhelper.trusted.LauncherActivity` |
| Dependency | `com.google.androidbrowserhelper:androidbrowserhelper:2.5.0` (pinned, see below) |
| Signing key | `~/.android-keys/english-listening.jks` (outside the repo) |

`LauncherActivity` is **not** in `androidx.browser` — that library only has
`TrustedWebActivityIntentBuilder`. The activity comes from
`androidbrowserhelper`. The meta-data key names used in the manifest were read
out of `LauncherActivityMetadata.class` in the published AAR, not from memory.

### Why the dependency is pinned to 2.5.0

The newer releases pull in AndroidX libraries that need a newer build toolchain
than the JDK-17/AGP 8.4.0/compileSdk 34 combination this host has:

| version | transitive dependency | needs |
|---|---|---|
| 2.7.3 | `androidx.core:core:1.17.0` | AGP 8.9.1+, compileSdk 36 |
| 2.6.2 | `androidx.browser:browser:1.9.0-alpha04` | AGP 8.9.1+, compileSdk 36 |
| **2.5.0** | `annotation:1.1.0`, `core:1.0.2`, `browser:1.4.0` | fine with compileSdk 34 |

2.5.0 has the same `LauncherActivity` and the same meta-data keys. To move up,
raise AGP, Gradle and compileSdk together (and install the matching platform).

### The launcher icon needs its own intent filter

`MAIN` + `LAUNCHER` is a separate `<intent-filter>` from the `VIEW`/`autoVerify`
one. With only the `VIEW` filter the APK installs fine but gets **no app-drawer
icon**, so there is no way to start it. `aapt2 dump badging` is the quick check:

```bash
aapt2 dump badging app-release.apk | grep launchable-activity
# launchable-activity: name='com.google.androidbrowserhelper.trusted.LauncherActivity' ...
```

An empty result means the icon filter is missing.

## Full screen needs assetlinks.json

Chrome only drops the URL bar if it can verify that the app and the site belong
together. That is what `static/.well-known/assetlinks.json` in the site repo is:
it lists the application ID and the SHA-256 of the **signing certificate**.

```bash
# the fingerprint that must match assetlinks.json
keytool -list -v -keystore ~/.android-keys/english-listening.jks \
        -alias english-listening | grep SHA256
```

Currently published:

    78:D7:79:EB:80:60:9B:1F:BC:60:2A:4A:20:68:EE:7C:C7:04:70:6F:33:49:5D:E7:39:6F:47:D6:F8:A4:16:80

If verification fails the app still works, it just shows a normal Custom Tab
*with* a URL bar. Check it with:

```bash
adb shell pm get-app-links io.github.mapengfeiglasgow.englishlistening
```

## Keeping the signing key

`~/.android-keys/english-listening.jks` (chmod 600) plus the generated
`~/.android-keys/password.txt` are **not** in git and must be backed up
somewhere safe. Android identifies an app by its signing key: lose it and you can
never ship an update over the installed app — you would have to uninstall first.
It also has to stay the one named in `assetlinks.json`, or the app loses
full-screen mode.

## Rebuilding

Needs **JDK 17** (not the system Java 8), the Android SDK (platform 34,
build-tools 34.0.0) and Gradle 8.6+. On this host:

```bash
export JAVA_HOME=/home/deepseek-harness/android-build/jdk17
export ANDROID_HOME=/home/deepseek-harness/android-build/sdk
cd android
/home/deepseek-harness/android-build/gradle/gradle-8.7/bin/gradle assembleRelease
```

If the SDK is elsewhere, point `ANDROID_HOME` (or `sdk.dir` in a
`local.properties`, which is gitignored) at it. `TWA_KEYSTORE`,
`TWA_KEYSTORE_PASSWORD` and `TWA_KEY_ALIAS` override the signing defaults.

The signed APK lands at:

    android/app/build/outputs/apk/release/app-release.apk

Verify it without a device:

```bash
$ANDROID_HOME/build-tools/34.0.0/apksigner verify --print-certs \
    android/app/build/outputs/apk/release/app-release.apk
$ANDROID_HOME/build-tools/34.0.0/aapt2 dump badging \
    android/app/build/outputs/apk/release/app-release.apk
```

## Shipping an update

Bump `versionCode` (and usually `versionName`) in `app/build.gradle`, rebuild,
and install the new APK over the old one — same signing key, so Android accepts
it as an update. Nothing else changes: the content is the live site.

## Installing on the phone

The APK is not distributed through Google Play, so Android will ask you to allow
installing unknown apps for whichever app you open it from (browser or Files).
Install, then open "English Listening". If the URL bar is visible, the
assetlinks check failed — see above.

## The site is also installable without the APK

Because `static/manifest.json` and the icons are published, the site can also be
added straight from Chrome ("Add to Home screen"). That gives the same
standalone, no-address-bar experience on Android and iOS without any build —
handy as a fallback, and it is what the TWA reuses for its splash screen.
