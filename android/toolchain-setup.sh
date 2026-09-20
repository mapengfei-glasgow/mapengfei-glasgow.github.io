#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Fetch the Android build toolchain used by android/ into one prefix.
#
# Nothing here needs root: the JDK, the Android SDK and Gradle are all unpacked
# into $PREFIX and are only referenced through environment variables.
#
#   ./android/toolchain-setup.sh [PREFIX]        # default ~/android-build
#
# Re-running is safe: anything already unpacked is left alone. Downloads land in
# $PREFIX/dl and are kept, so a re-run after a partial failure does not refetch.
#
# If a proxy is needed, export http_proxy/https_proxy first (this host needs
# http://127.0.0.1:7891). curl picks those up; the Android SDK manager ignores
# them, so they are translated into -Dhttp(s).proxyHost JVM properties below.
# ---------------------------------------------------------------------------
set -euo pipefail

PREFIX="${1:-${ANDROID_BUILD_ROOT:-$HOME/android-build}}"
JDK_MAJOR=17
GRADLE_VERSION=8.7
CMDLINE_TOOLS_BUILD=9862592        # cmdline-tools "latest" from Google's repo XML
# Note the quotes: sdkmanager package names contain a semicolon, which is a
# command separator to the shell if left bare.
SDK_PACKAGES=(platform-tools "platforms;android-34" "build-tools;34.0.0")
SDK_ROOT="$PREFIX/sdk"
DL="$PREFIX/dl"

log() { printf '[toolchain] %s\n' "$*"; }
die() { printf '[toolchain] ERROR: %s\n' "$*" >&2; exit 1; }

mkdir -p "$PREFIX" "$DL"

# --- proxy for the SDK manager --------------------------------------------
# The SDK manager is a JVM app and does not read http_proxy.
SDKMANAGER_OPTS_EXTRA=""
proxy_url="${https_proxy:-${http_proxy:-}}"
if [ -n "$proxy_url" ]; then
    # strip scheme and any trailing slash/path -> host:port
    proxy_hostport="${proxy_url#*://}"
    proxy_hostport="${proxy_hostport%%/*}"
    proxy_host="${proxy_hostport%%:*}"
    proxy_port="${proxy_hostport##*:}"
    if [ -n "$proxy_host" ] && [ "$proxy_host" != "$proxy_port" ]; then
        SDKMANAGER_OPTS_EXTRA="-Dhttp.proxyHost=$proxy_host -Dhttp.proxyPort=$proxy_port"
        SDKMANAGER_OPTS_EXTRA="$SDKMANAGER_OPTS_EXTRA -Dhttps.proxyHost=$proxy_host -Dhttps.proxyPort=$proxy_port"
        log "proxy for the SDK manager: $proxy_host:$proxy_port"
    fi
fi

# --- 1. JDK ---------------------------------------------------------------
JDK_DIR="$PREFIX/jdk$JDK_MAJOR"
if [ -x "$JDK_DIR/bin/javac" ]; then
    log "JDK already present: $JDK_DIR ($("$JDK_DIR/bin/java" -version 2>&1 | head -1))"
else
    log "resolving the latest Temurin JDK $JDK_MAJOR (linux x64)"
    jdk_url=$(curl -sS --max-time 60 \
        "https://api.adoptium.net/v3/assets/latest/$JDK_MAJOR/hotspot?architecture=x64&image_type=jdk&os=linux&vendor=eclipse" \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["binary"]["package"]["link"])')
    [ -n "$jdk_url" ] || die "could not resolve a JDK $JDK_MAJOR download"
    log "downloading $(basename "$jdk_url")"
    curl -sS -L --max-time 1800 -o "$DL/jdk$JDK_MAJOR.tar.gz" "$jdk_url"
    mkdir -p "$JDK_DIR"
    tar -xzf "$DL/jdk$JDK_MAJOR.tar.gz" -C "$JDK_DIR" --strip-components=1
    log "JDK unpacked: $("$JDK_DIR/bin/java" -version 2>&1 | head -1)"
fi

# --- 2. Gradle ------------------------------------------------------------
GRADLE_DIR="$PREFIX/gradle/gradle-$GRADLE_VERSION"
if [ -x "$GRADLE_DIR/bin/gradle" ]; then
    log "Gradle already present: $GRADLE_DIR"
else
    log "downloading Gradle $GRADLE_VERSION"
    curl -sS -L --max-time 1800 -o "$DL/gradle-$GRADLE_VERSION-bin.zip" \
        "https://services.gradle.org/distributions/gradle-$GRADLE_VERSION-bin.zip"
    mkdir -p "$PREFIX/gradle"
    unzip -q -o "$DL/gradle-$GRADLE_VERSION-bin.zip" -d "$PREFIX/gradle"
    log "Gradle unpacked: $GRADLE_DIR"
fi

# --- 3. Android SDK -------------------------------------------------------
export JAVA_HOME="$JDK_DIR"
export ANDROID_HOME="$SDK_ROOT"
SDKM="$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager"

if [ -x "$SDKM" ]; then
    log "cmdline-tools already present"
else
    log "downloading Android cmdline-tools ($CMDLINE_TOOLS_BUILD)"
    curl -sS -L --max-time 1800 -o "$DL/cmdline-tools.zip" \
        "https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_BUILD}_latest.zip"
    rm -rf "$PREFIX/.cmdtools-tmp" && mkdir -p "$PREFIX/.cmdtools-tmp"
    unzip -q -o "$DL/cmdline-tools.zip" -d "$PREFIX/.cmdtools-tmp"
    mkdir -p "$SDK_ROOT/cmdline-tools"
    rm -rf "$SDK_ROOT/cmdline-tools/latest"
    mv "$PREFIX/.cmdtools-tmp/cmdline-tools" "$SDK_ROOT/cmdline-tools/latest"
    rmdir "$PREFIX/.cmdtools-tmp"
    log "cmdline-tools unpacked: $SDKM"
fi

export SDKMANAGER_OPTS="${SDKMANAGER_OPTS_EXTRA} -Dcom.android.sdklib.toolsdir=$SDK_ROOT/cmdline-tools/latest"

log "accepting SDK licences"
yes 2>/dev/null | "$SDKM" --sdk_root="$SDK_ROOT" --licenses >/dev/null 2>&1 || true

log "installing: ${SDK_PACKAGES[*]}"
"$SDKM" --sdk_root="$SDK_ROOT" "${SDK_PACKAGES[@]}"

# --- summary --------------------------------------------------------------
cat <<EOF

Toolchain ready. Build with:

  export JAVA_HOME=$JDK_DIR
  export ANDROID_HOME=$SDK_ROOT
  export PATH="\$JAVA_HOME/bin:\$PATH"
  cd android && $GRADLE_DIR/bin/gradle --no-daemon assembleRelease

Installed:
EOF
"$SDKM" --sdk_root="$SDK_ROOT" --list_installed 2>/dev/null | sed -n '/Installed packages/,$p' | tail -n +3
