# Food Admin Curation Actions

## Purpose

This document describes the first Django Admin curation actions for global foods.

The goal is to allow an admin to curate imported foods without changing models, importers or picker logic.

## Actions

The first curation actions are:

- Mark selected foods as core
- Mark selected foods as extended
- Mark selected foods as hidden
- Mark selected foods as rejected
- Mark selected foods as verified
- Mark selected foods as unverified
- Mark selected foods as active
- Mark selected foods as inactive

## Visibility meaning

Core:

Curated foods intended to be shown first in the picker.

Extended:

Valid global foods that may be searchable but are not part of the curated core catalog.

Hidden:

Foods stored for traceability or future review, but not exposed in normal picker flows.

Rejected:

Foods that should not be exposed. Rejected foods are also marked inactive by the admin action.

## Active meaning

Active foods may be exposed if their visibility allows it.

Inactive foods are excluded from picker/global food queries.

## Verified meaning

Verified foods have been reviewed or approved by an admin.

Verification does not automatically make a food core.

## Data safety

These admin actions are explicit curation tools.

They do not modify nutrition values.

They do not modify meals.

They do not modify daily plans.

They do not modify historical snapshots.

## Current scope

This block only adds admin curation actions.

It does not add a custom admin UI.

It does not add bulk import.

It does not add Spanish aliases.

It does not change picker rendering.