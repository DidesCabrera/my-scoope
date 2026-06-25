# Food Picker Display Name Contract

## Purpose

This document describes the display_name field in the food picker payload.

The goal is to let the backend provide a localized display name without changing the original Food.name.

## Why display_name exists

Food.name may come from an external source such as USDA.

Example:

Chicken breast, cooked

For Chilean or Spanish-speaking users, the picker should eventually show:

Pechuga de pollo cocida

The display_name field allows this without overwriting Food.name.

## Payload fields

The picker payload now includes:

- name
- display_name
- search_text

## Field meaning

name:

Original food name stored in Food.

display_name:

Localized display name resolved for the current product locale.

If no localized name exists, display_name falls back to name.

search_text:

Searchable text that may include name, canonical_name and aliases.

## Current locale

The current default locale is:

- language: es
- country: CL

This can be generalized later.

## Current scope

This block only adds display_name to the backend payload.

It does not yet change JavaScript rendering.

The next block will make the picker visually render display_name.