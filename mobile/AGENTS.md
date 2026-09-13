# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v57.0.0/ before writing any code.

## Fast product iteration

Use `../scripts/ci_mobile_iteration.sh` while iterating on routine mobile UI and
behavior. It runs lint, TypeScript validation, and the mobile contract/unit
suite without paying for dependency audits and a production-style web export
on every visual adjustment.

Use `../scripts/ci_mobile_checks.sh` once before final integration, or earlier
when changing dependencies, Expo/native configuration, release settings, or
other critical mobile infrastructure. Keep the staging development client
pointed at staging services when local authentication cannot represent the
real environment.
