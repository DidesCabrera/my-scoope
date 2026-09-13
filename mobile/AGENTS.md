# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

## Fast product iteration

For visual UI iteration, use `../scripts/ci_mobile_visual_check.sh` and pass only
the directly related test file when one exists. It lints changed files without
running the global typecheck or all mobile tests.

Use `../scripts/ci_mobile_iteration.sh` once when a mobile refinement stage is
closed. It runs lint, TypeScript validation, and the mobile contract/unit suite.

Use `../scripts/ci_mobile_checks.sh` once before final integration, or earlier
when changing dependencies, Expo/native configuration, release settings, or
other critical mobile infrastructure. Keep the staging development client
pointed at staging services when local authentication cannot represent the
real environment.
