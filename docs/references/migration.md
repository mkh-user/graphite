# Migration reference

This document provides the API reference for `Migration` class of `graphite`

Items in this list can be accessed with `from graphite.Migration import ...` (lowest level import recommended)

# Functions

## `convert_pickle_to_json(pickle_file: str, json_file: str, delete_original: bool = False) -> bool`

Convert a pickle file to JSON format

Returns True at success, otherwise False

## `detect_pickle_and_convert_to_json(directory: str, pattern: str = "*.db", delete_originals: bool = False)`

Find and convert all pickle files in a directory

Calls `convert_pickle_to_json()` for each detected file
