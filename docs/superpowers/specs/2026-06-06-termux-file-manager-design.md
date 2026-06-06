# Termux `/file` File Manager Design

## Goal

Add an inline file manager to the Codex TUI composer for Termux users. When the user types a standalone `/file` token inside a prompt, Codex immediately opens a picker rooted at `/storage/emulated/0`. Selecting a file replaces that `/file` token with the selected absolute path.

Example:

```text
przeanalizuj ten plik /file
```

After choosing `/storage/emulated/0/dlatermux/skrypt.js`:

```text
przeanalizuj ten plik /storage/emulated/0/dlatermux/skrypt.js
```

## Scope

This feature targets the Rust TUI composer in `codex-rs/tui2`. It should use the existing bottom-pane popup pattern instead of launching an Android GUI picker. The existing `@` file search remains unchanged and continues to search within the workspace.

The first implementation should support selecting files only. Directory navigation is part of the picker, but choosing a directory inserts nothing; Enter on a directory opens it.

## Trigger

The picker opens as soon as the composer detects a standalone `/file` token. A standalone token is delimited by whitespace or text boundaries. It should match:

- `/file`
- `przeanalizuj /file`
- `/file potem opisz`

It should not match:

- `abc/file`
- `/filename`
- `text/file`

If the user dismisses the picker with Esc while the cursor still targets the same `/file` token, the picker should not immediately reopen until the token changes or the user moves away and edits again.

## UI And Controls

Add a new popup state to the composer, separate from slash commands, `@` file search, and skill mentions.

The popup starts in `/storage/emulated/0` and displays:

- `..` when the current directory has a parent that can be navigated to.
- Directories.
- Files.

Directories should be visually distinguishable using a trailing slash. The list should keep stable selection and scrolling behavior by reusing the existing selection popup primitives where practical.

Controls:

- Up / Ctrl-P: move selection up.
- Down / Ctrl-N: move selection down.
- Enter: open the selected directory, or select the selected file.
- Tab: select the highlighted file, matching existing popup completion behavior.
- Esc: close without changing composer text.
- `s`: cycle sorting by `name`, `date`, and `type`.
- `r`: reverse the current sort direction.

The popup footer or empty-state row should expose the active sort mode in concise text, for example `sort: name asc`.

## Sorting

The file manager supports three sort keys:

- `name`: case-insensitive name comparison.
- `date`: filesystem modified time, with entries lacking metadata placed last.
- `type`: directories first, then file extension, then name.

Directories should always appear before files unless the selected sort mode is explicitly `date`. For `type`, directories are grouped first by definition.

Sort direction applies to the active sort key. The default is `name` ascending.

## Data Model

Introduce a small file-manager model in `tui2/src/bottom_pane`, for example `file_manager_popup.rs`:

- `FileManagerPopup`
- `FileManagerEntry`
- `FileManagerSortKey`
- `SortDirection`

Each entry stores display name, absolute path, entry kind, extension, and optional modified time. Directory reads should use `std::fs::read_dir` and recover per-entry metadata failures by keeping the entry with missing metadata where possible.

## Composer Integration

Extend `ActivePopup` with `FileManager(FileManagerPopup)`.

Add token helpers parallel to the existing prefixed-token helpers, but specialized for exact standalone token replacement:

- Detect the active `/file` token under or immediately before the cursor.
- Return its byte range.
- Replace that byte range with the selected absolute path plus a trailing space.

Path insertion should quote paths only if the existing local prompt parsing requires it. For this feature, the first implementation inserts the raw absolute path, matching the requested example.

## Error Handling

If `/storage/emulated/0` cannot be read, the popup should render a clear one-line error and stay open so the user can dismiss it with Esc.

If a directory cannot be opened, keep the previous directory visible and show the error in the popup.

If the selected path disappears before selection, refresh the current directory and keep the picker open.

## Tests

Add focused tests in the TUI crate:

- Standalone `/file` detection succeeds and non-standalone text does not trigger it.
- Replacing a `/file` token preserves surrounding text and places the cursor after the inserted path plus trailing space.
- Directory entries sort by name, modified date, and type.
- Esc dismissal does not immediately reopen for the same token.

Run at minimum:

```sh
just fmt
cargo test -p codex-tui2
```

Before finalizing implementation, run the scoped lint fixer requested by repo instructions:

```sh
just fix -p codex-tui2
```
