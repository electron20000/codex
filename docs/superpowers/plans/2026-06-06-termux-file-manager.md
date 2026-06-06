# Termux File Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inline `/file` picker to the Codex TUI2 composer that browses `/storage/emulated/0` and replaces `/file` with the selected absolute file path.

**Architecture:** Add a focused `FileManagerPopup` beside the existing bottom-pane popup components, using `ScrollState` and `selection_popup_common::render_rows` for list behavior. Integrate it into `ChatComposer` as a new `ActivePopup` variant and add exact `/file` token detection/replacement helpers. Keep the existing `@` file search and slash command popup behavior unchanged.

**Tech Stack:** Rust, ratatui, crossterm, existing `codex-tui2` bottom pane components, `std::fs`.

---

## File Structure

- Create `codex-rs/tui2/src/bottom_pane/file_manager_popup.rs`
  - Owns directory reading, entry metadata, sorting, navigation state, selected entry behavior, and popup rendering.
- Modify `codex-rs/tui2/src/bottom_pane/mod.rs`
  - Registers the new module.
- Modify `codex-rs/tui2/src/bottom_pane/chat_composer.rs`
  - Adds `ActivePopup::FileManager`, exact `/file` token helpers, dismissal state, key handling, layout/render integration, and unit tests.
- Existing file `codex-rs/tui2/src/bottom_pane/scroll_state.rs`
  - Reused unchanged.
- Existing file `codex-rs/tui2/src/bottom_pane/selection_popup_common.rs`
  - Reused unchanged.

### Task 1: File Manager Popup Model

**Files:**
- Create: `codex-rs/tui2/src/bottom_pane/file_manager_popup.rs`
- Modify: `codex-rs/tui2/src/bottom_pane/mod.rs`

- [ ] **Step 1: Write failing sort and navigation tests**

Add this test module at the bottom of the new file. The implementation above it can initially contain only type stubs if needed.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use std::time::SystemTime;

    fn entry(name: &str, kind: FileManagerEntryKind, modified_secs: Option<u64>) -> FileManagerEntry {
        FileManagerEntry {
            name: name.to_string(),
            path: PathBuf::from(format!("/root/{name}")),
            kind,
            extension: Path::new(name)
                .extension()
                .and_then(|ext| ext.to_str())
                .map(str::to_ascii_lowercase),
            modified: modified_secs.map(|secs| SystemTime::UNIX_EPOCH + Duration::from_secs(secs)),
        }
    }

    #[test]
    fn sorts_by_name_with_directories_first() {
        let mut entries = vec![
            entry("z.txt", FileManagerEntryKind::File, Some(10)),
            entry("beta", FileManagerEntryKind::Directory, Some(20)),
            entry("a.txt", FileManagerEntryKind::File, Some(30)),
            entry("Alpha", FileManagerEntryKind::Directory, Some(40)),
        ];

        sort_entries(&mut entries, FileManagerSortKey::Name, SortDirection::Ascending);

        let names: Vec<_> = entries.iter().map(|entry| entry.name.as_str()).collect();
        assert_eq!(names, vec!["Alpha", "beta", "a.txt", "z.txt"]);
    }

    #[test]
    fn sorts_by_date_without_forcing_directories_first() {
        let mut entries = vec![
            entry("older_dir", FileManagerEntryKind::Directory, Some(10)),
            entry("newer_file.txt", FileManagerEntryKind::File, Some(30)),
            entry("middle_dir", FileManagerEntryKind::Directory, Some(20)),
        ];

        sort_entries(&mut entries, FileManagerSortKey::Date, SortDirection::Descending);

        let names: Vec<_> = entries.iter().map(|entry| entry.name.as_str()).collect();
        assert_eq!(names, vec!["newer_file.txt", "middle_dir", "older_dir"]);
    }

    #[test]
    fn sorts_by_type_then_name_with_directories_first() {
        let mut entries = vec![
            entry("z.md", FileManagerEntryKind::File, Some(10)),
            entry("src", FileManagerEntryKind::Directory, Some(10)),
            entry("a.js", FileManagerEntryKind::File, Some(10)),
            entry("b.js", FileManagerEntryKind::File, Some(10)),
        ];

        sort_entries(&mut entries, FileManagerSortKey::Type, SortDirection::Ascending);

        let names: Vec<_> = entries.iter().map(|entry| entry.name.as_str()).collect();
        assert_eq!(names, vec!["src", "a.js", "b.js", "z.md"]);
    }

    #[test]
    fn open_directory_refreshes_entries_and_keeps_files_selectable() {
        let tmp = tempfile::tempdir().expect("tempdir");
        let dir = tmp.path().join("folder");
        std::fs::create_dir(&dir).expect("create folder");
        std::fs::write(dir.join("note.txt"), "hello").expect("write file");

        let mut popup = FileManagerPopup::new_at(tmp.path().to_path_buf());
        assert!(popup.entries().iter().any(|entry| entry.name == "folder"));

        let folder_idx = popup
            .entries()
            .iter()
            .position(|entry| entry.name == "folder")
            .expect("folder entry");
        popup.set_selected_idx_for_test(folder_idx);
        let outcome = popup.activate_selected();
        assert_eq!(outcome, FileManagerSelection::OpenedDirectory);
        assert_eq!(popup.current_dir(), dir.as_path());
        assert!(popup.entries().iter().any(|entry| entry.name == "note.txt"));
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```sh
cargo test -p codex-tui2 bottom_pane::file_manager_popup
```

Expected: compile failure because `file_manager_popup` types and functions are not implemented yet.

- [ ] **Step 3: Implement the popup model and renderer**

Create `codex-rs/tui2/src/bottom_pane/file_manager_popup.rs` with:

```rust
use std::cmp::Ordering;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::time::SystemTime;

use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::widgets::WidgetRef;

use super::popup_consts::MAX_POPUP_ROWS;
use super::scroll_state::ScrollState;
use super::selection_popup_common::GenericDisplayRow;
use super::selection_popup_common::render_rows;
use crate::render::Insets;
use crate::render::RectExt;

const DEFAULT_ROOT: &str = "/storage/emulated/0";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum FileManagerEntryKind {
    Parent,
    Directory,
    File,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct FileManagerEntry {
    pub(crate) name: String,
    pub(crate) path: PathBuf,
    pub(crate) kind: FileManagerEntryKind,
    pub(crate) extension: Option<String>,
    pub(crate) modified: Option<SystemTime>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum FileManagerSortKey {
    Name,
    Date,
    Type,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SortDirection {
    Ascending,
    Descending,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum FileManagerSelection {
    SelectedFile(PathBuf),
    OpenedDirectory,
    None,
}

pub(crate) struct FileManagerPopup {
    current_dir: PathBuf,
    entries: Vec<FileManagerEntry>,
    state: ScrollState,
    sort_key: FileManagerSortKey,
    sort_direction: SortDirection,
    error: Option<String>,
}

impl FileManagerPopup {
    pub(crate) fn new() -> Self {
        Self::new_at(PathBuf::from(DEFAULT_ROOT))
    }

    pub(crate) fn new_at(root: PathBuf) -> Self {
        let mut popup = Self {
            current_dir: root,
            entries: Vec::new(),
            state: ScrollState::new(),
            sort_key: FileManagerSortKey::Name,
            sort_direction: SortDirection::Ascending,
            error: None,
        };
        popup.refresh();
        popup
    }

    pub(crate) fn current_dir(&self) -> &Path {
        &self.current_dir
    }

    #[cfg(test)]
    pub(crate) fn entries(&self) -> &[FileManagerEntry] {
        &self.entries
    }

    #[cfg(test)]
    pub(crate) fn set_selected_idx_for_test(&mut self, idx: usize) {
        self.state.selected_idx = Some(idx);
        self.state.ensure_visible(self.entries.len(), self.entries.len().min(MAX_POPUP_ROWS));
    }

    pub(crate) fn calculate_required_height(&self) -> u16 {
        let header_rows = 1usize;
        let entry_rows = self.entries.len().clamp(1, MAX_POPUP_ROWS);
        (header_rows + entry_rows) as u16
    }

    pub(crate) fn move_up(&mut self) {
        let len = self.entries.len();
        self.state.move_up_wrap(len);
        self.state.ensure_visible(len, len.min(MAX_POPUP_ROWS));
    }

    pub(crate) fn move_down(&mut self) {
        let len = self.entries.len();
        self.state.move_down_wrap(len);
        self.state.ensure_visible(len, len.min(MAX_POPUP_ROWS));
    }

    pub(crate) fn cycle_sort_key(&mut self) {
        self.sort_key = match self.sort_key {
            FileManagerSortKey::Name => FileManagerSortKey::Date,
            FileManagerSortKey::Date => FileManagerSortKey::Type,
            FileManagerSortKey::Type => FileManagerSortKey::Name,
        };
        self.apply_sort();
    }

    pub(crate) fn reverse_sort_direction(&mut self) {
        self.sort_direction = match self.sort_direction {
            SortDirection::Ascending => SortDirection::Descending,
            SortDirection::Descending => SortDirection::Ascending,
        };
        self.apply_sort();
    }

    pub(crate) fn activate_selected(&mut self) -> FileManagerSelection {
        let Some(idx) = self.state.selected_idx else {
            return FileManagerSelection::None;
        };
        let Some(entry) = self.entries.get(idx).cloned() else {
            return FileManagerSelection::None;
        };

        match entry.kind {
            FileManagerEntryKind::Parent | FileManagerEntryKind::Directory => {
                self.open_directory(entry.path);
                FileManagerSelection::OpenedDirectory
            }
            FileManagerEntryKind::File => {
                if entry.path.is_file() {
                    FileManagerSelection::SelectedFile(entry.path)
                } else {
                    self.refresh();
                    FileManagerSelection::None
                }
            }
        }
    }

    fn open_directory(&mut self, path: PathBuf) {
        let previous = self.current_dir.clone();
        self.current_dir = path;
        self.refresh();
        if self.error.is_some() {
            self.current_dir = previous;
            self.refresh();
        }
    }

    fn refresh(&mut self) {
        match read_entries(&self.current_dir) {
            Ok(mut entries) => {
                sort_entries(&mut entries, self.sort_key, self.sort_direction);
                self.entries = entries;
                self.error = None;
                self.state.clamp_selection(self.entries.len());
                self.state
                    .ensure_visible(self.entries.len(), self.entries.len().min(MAX_POPUP_ROWS));
            }
            Err(err) => {
                self.entries.clear();
                self.error = Some(format!("cannot read {}: {err}", self.current_dir.display()));
                self.state.reset();
            }
        }
    }

    fn apply_sort(&mut self) {
        sort_entries(&mut self.entries, self.sort_key, self.sort_direction);
        self.state.clamp_selection(self.entries.len());
        self.state
            .ensure_visible(self.entries.len(), self.entries.len().min(MAX_POPUP_ROWS));
    }

    fn sort_label(&self) -> String {
        let key = match self.sort_key {
            FileManagerSortKey::Name => "name",
            FileManagerSortKey::Date => "date",
            FileManagerSortKey::Type => "type",
        };
        let direction = match self.sort_direction {
            SortDirection::Ascending => "asc",
            SortDirection::Descending => "desc",
        };
        format!("{}  sort: {key} {direction}", self.current_dir.display())
    }
}

fn read_entries(dir: &Path) -> std::io::Result<Vec<FileManagerEntry>> {
    let mut entries = Vec::new();

    if let Some(parent) = dir.parent() {
        entries.push(FileManagerEntry {
            name: "..".to_string(),
            path: parent.to_path_buf(),
            kind: FileManagerEntryKind::Parent,
            extension: None,
            modified: None,
        });
    }

    for entry_result in fs::read_dir(dir)? {
        let entry = entry_result?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().into_owned();
        let metadata = entry.metadata().ok();
        let is_dir = metadata.as_ref().is_some_and(fs::Metadata::is_dir);
        let kind = if is_dir {
            FileManagerEntryKind::Directory
        } else {
            FileManagerEntryKind::File
        };
        let extension = path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(str::to_ascii_lowercase);
        let modified = metadata.and_then(|metadata| metadata.modified().ok());

        entries.push(FileManagerEntry {
            name,
            path,
            kind,
            extension,
            modified,
        });
    }

    Ok(entries)
}

pub(crate) fn sort_entries(
    entries: &mut [FileManagerEntry],
    sort_key: FileManagerSortKey,
    direction: SortDirection,
) {
    entries.sort_by(|a, b| compare_entries(a, b, sort_key, direction));
}

fn compare_entries(
    a: &FileManagerEntry,
    b: &FileManagerEntry,
    sort_key: FileManagerSortKey,
    direction: SortDirection,
) -> Ordering {
    if a.kind == FileManagerEntryKind::Parent {
        return Ordering::Less;
    }
    if b.kind == FileManagerEntryKind::Parent {
        return Ordering::Greater;
    }

    if matches!(sort_key, FileManagerSortKey::Date) {
        let metadata_order = match (a.modified, b.modified) {
            (Some(_), None) => Ordering::Less,
            (None, Some(_)) => Ordering::Greater,
            _ => Ordering::Equal,
        };
        if metadata_order != Ordering::Equal {
            return metadata_order;
        }
    }

    let base = match sort_key {
        FileManagerSortKey::Name => compare_kind_group(a, b)
            .then_with(|| a.name.to_ascii_lowercase().cmp(&b.name.to_ascii_lowercase())),
        FileManagerSortKey::Date => compare_modified(a, b)
            .then_with(|| a.name.to_ascii_lowercase().cmp(&b.name.to_ascii_lowercase())),
        FileManagerSortKey::Type => compare_kind_group(a, b)
            .then_with(|| a.extension.cmp(&b.extension))
            .then_with(|| a.name.to_ascii_lowercase().cmp(&b.name.to_ascii_lowercase())),
    };

    match direction {
        SortDirection::Ascending => base,
        SortDirection::Descending => base.reverse(),
    }
}

fn compare_kind_group(a: &FileManagerEntry, b: &FileManagerEntry) -> Ordering {
    let rank = |kind| match kind {
        FileManagerEntryKind::Parent => 0,
        FileManagerEntryKind::Directory => 1,
        FileManagerEntryKind::File => 2,
    };
    rank(a.kind).cmp(&rank(b.kind))
}

fn compare_modified(a: &FileManagerEntry, b: &FileManagerEntry) -> Ordering {
    match (a.modified, b.modified) {
        (Some(a_time), Some(b_time)) => a_time.cmp(&b_time),
        (Some(_), None) => Ordering::Equal,
        (None, Some(_)) => Ordering::Equal,
        (None, None) => Ordering::Equal,
    }
}

impl WidgetRef for &FileManagerPopup {
    fn render_ref(&self, area: Rect, buf: &mut Buffer) {
        let [header_area, rows_area] =
            ratatui::layout::Layout::vertical([ratatui::layout::Constraint::Length(1), ratatui::layout::Constraint::Min(1)])
                .areas(area);
        ratatui::text::Line::from(self.sort_label()).render_ref(header_area.inset(Insets::tlbr(0, 2, 0, 0)), buf);

        let rows: Vec<GenericDisplayRow> = self
            .entries
            .iter()
            .map(|entry| {
                let name = match entry.kind {
                    FileManagerEntryKind::Parent => "..".to_string(),
                    FileManagerEntryKind::Directory => format!("{}/", entry.name),
                    FileManagerEntryKind::File => entry.name.clone(),
                };
                GenericDisplayRow {
                    name,
                    match_indices: None,
                    display_shortcut: None,
                    description: None,
                    wrap_indent: None,
                }
            })
            .collect();

        let empty_message = self.error.as_deref().unwrap_or("empty directory");
        render_rows(
            rows_area.inset(Insets::tlbr(0, 2, 0, 0)),
            buf,
            &rows,
            &self.state,
            MAX_POPUP_ROWS,
            empty_message,
        );
    }
}
```

Modify `codex-rs/tui2/src/bottom_pane/mod.rs`:

```rust
mod file_manager_popup;
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```sh
cargo test -p codex-tui2 bottom_pane::file_manager_popup
```

Expected: all `file_manager_popup` tests pass.

- [ ] **Step 5: Commit**

```sh
git add codex-rs/tui2/src/bottom_pane/file_manager_popup.rs codex-rs/tui2/src/bottom_pane/mod.rs
git commit -m "Add TUI2 file manager popup model"
```

### Task 2: `/file` Token Detection And Replacement

**Files:**
- Modify: `codex-rs/tui2/src/bottom_pane/chat_composer.rs`

- [ ] **Step 1: Write failing token tests**

Add tests near the existing `current_prefixed_token` tests in `chat_composer.rs`:

```rust
fn test_composer() -> ChatComposer {
    let (tx, _rx) = unbounded_channel::<AppEvent>();
    ChatComposer::new(
        true,
        AppEventSender::new(tx),
        false,
        "Ask Codex to do anything".to_string(),
        false,
    )
}

#[test]
fn current_file_manager_token_range_detects_standalone_file_token() {
    let cases = [
        ("/file", 5, Some(0..5)),
        ("przeanalizuj /file", 17, Some(12..17)),
        ("/file potem opisz", 2, Some(0..5)),
        ("abc/file", 8, None),
        ("/filename", 5, None),
        ("text/file", 4, None),
    ];

    for (text, cursor, expected) in cases {
        let mut composer = test_composer();
        composer.set_text_content(text.to_string());
        composer.textarea.set_cursor(cursor);
        assert_eq!(
            ChatComposer::current_file_manager_token_range(&composer.textarea),
            expected,
            "case {text:?}"
        );
    }
}

#[test]
fn insert_selected_file_manager_path_replaces_file_token_and_preserves_surrounding_text() {
    let mut composer = test_composer();
    composer.set_text_content("przeanalizuj /file potem".to_string());
    composer.textarea.set_cursor("przeanalizuj /file".len());

    composer.insert_selected_file_manager_path(Path::new("/storage/emulated/0/dlatermux/skrypt.js"));

    assert_eq!(
        composer.textarea.text(),
        "przeanalizuj /storage/emulated/0/dlatermux/skrypt.js  potem"
    );
    assert_eq!(
        composer.textarea.cursor(),
        "przeanalizuj /storage/emulated/0/dlatermux/skrypt.js ".len()
    );
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```sh
cargo test -p codex-tui2 current_file_manager_token_range_detects_standalone_file_token insert_selected_file_manager_path_replaces_file_token_and_preserves_surrounding_text
```

Expected: compile failure because the two helper methods do not exist.

- [ ] **Step 3: Implement token range and replacement helpers**

Add `use std::ops::Range;` near the other imports if not already present.

Add methods inside `impl ChatComposer` near `current_prefixed_token`:

```rust
fn current_file_manager_token_range(textarea: &TextArea) -> Option<Range<usize>> {
    let cursor_offset = textarea.cursor();
    let text = textarea.text();
    let safe_cursor = Self::clamp_to_char_boundary(text, cursor_offset);

    let before_cursor = &text[..safe_cursor];
    let after_cursor = &text[safe_cursor..];

    let start_idx = before_cursor
        .char_indices()
        .rfind(|(_, c)| c.is_whitespace())
        .map(|(idx, c)| idx + c.len_utf8())
        .unwrap_or(0);
    let end_rel_idx = after_cursor
        .char_indices()
        .find(|(_, c)| c.is_whitespace())
        .map(|(idx, _)| idx)
        .unwrap_or(after_cursor.len());
    let end_idx = safe_cursor + end_rel_idx;

    if text.get(start_idx..end_idx) == Some("/file") {
        Some(start_idx..end_idx)
    } else {
        None
    }
}

fn insert_selected_file_manager_path(&mut self, path: &Path) {
    let Some(range) = Self::current_file_manager_token_range(&self.textarea) else {
        return;
    };
    let inserted = path.display().to_string();
    let text = self.textarea.text();
    let mut new_text =
        String::with_capacity(text.len() - (range.end - range.start) + inserted.len() + 1);
    new_text.push_str(&text[..range.start]);
    new_text.push_str(&inserted);
    new_text.push(' ');
    new_text.push_str(&text[range.end..]);

    let new_cursor = range.start.saturating_add(inserted.len()).saturating_add(1);
    self.textarea.set_text(&new_text);
    self.textarea.set_cursor(new_cursor);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```sh
cargo test -p codex-tui2 current_file_manager_token_range_detects_standalone_file_token insert_selected_file_manager_path_replaces_file_token_and_preserves_surrounding_text
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```sh
git add codex-rs/tui2/src/bottom_pane/chat_composer.rs
git commit -m "Detect and replace file manager token"
```

### Task 3: Composer Popup Integration

**Files:**
- Modify: `codex-rs/tui2/src/bottom_pane/chat_composer.rs`

- [ ] **Step 1: Write failing integration tests**

Add tests near other composer popup tests:

```rust
#[test]
fn typing_file_token_opens_file_manager_popup_immediately() {
    let mut composer = test_composer();

    for ch in "/file".chars() {
        composer.handle_key_event(KeyEvent::new(KeyCode::Char(ch), KeyModifiers::NONE));
    }

    assert!(matches!(composer.active_popup, ActivePopup::FileManager(_)));
}

#[test]
fn esc_dismisses_file_manager_popup_without_immediate_reopen() {
    let mut composer = test_composer();
    composer.set_text_content("/file".to_string());
    composer.textarea.set_cursor("/file".len());
    composer.sync_popups();
    assert!(matches!(composer.active_popup, ActivePopup::FileManager(_)));

    composer.handle_key_event(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE));

    assert!(matches!(composer.active_popup, ActivePopup::None));
    composer.sync_popups();
    assert!(matches!(composer.active_popup, ActivePopup::None));
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```sh
cargo test -p codex-tui2 typing_file_token_opens_file_manager_popup_immediately esc_dismisses_file_manager_popup_without_immediate_reopen
```

Expected: compile failure because `ActivePopup::FileManager` and sync logic do not exist.

- [ ] **Step 3: Add popup state fields and imports**

Modify imports in `chat_composer.rs`:

```rust
use super::file_manager_popup::FileManagerPopup;
use super::file_manager_popup::FileManagerSelection;
```

Add a field to `ChatComposer`:

```rust
dismissed_file_manager_token_range: Option<std::ops::Range<usize>>,
```

Initialize it in `ChatComposer::new`:

```rust
dismissed_file_manager_token_range: None,
```

Extend `ActivePopup`:

```rust
FileManager(FileManagerPopup),
```

- [ ] **Step 4: Wire layout, height, render, and dispatcher**

Add `FileManager` handling wherever `ActivePopup` is matched:

```rust
ActivePopup::FileManager(popup) => Constraint::Max(popup.calculate_required_height()),
```

```rust
ActivePopup::FileManager(_) => self.handle_key_event_with_file_manager_popup(key_event),
```

```rust
ActivePopup::FileManager(c) => c.calculate_required_height(),
```

```rust
ActivePopup::FileManager(popup) => {
    popup.render_ref(popup_rect, buf);
}
```

- [ ] **Step 5: Implement file manager key handling**

Add this method near other popup key handlers:

```rust
fn handle_key_event_with_file_manager_popup(
    &mut self,
    key_event: KeyEvent,
) -> (InputResult, bool) {
    if self.handle_shortcut_overlay_key(&key_event) {
        return (InputResult::None, true);
    }

    let ActivePopup::FileManager(popup) = &mut self.active_popup else {
        unreachable!();
    };

    match key_event {
        KeyEvent {
            code: KeyCode::Up, ..
        }
        | KeyEvent {
            code: KeyCode::Char('p'),
            modifiers: KeyModifiers::CONTROL,
            ..
        } => {
            popup.move_up();
            (InputResult::None, true)
        }
        KeyEvent {
            code: KeyCode::Down,
            ..
        }
        | KeyEvent {
            code: KeyCode::Char('n'),
            modifiers: KeyModifiers::CONTROL,
            ..
        } => {
            popup.move_down();
            (InputResult::None, true)
        }
        KeyEvent {
            code: KeyCode::Char('s'),
            modifiers: KeyModifiers::NONE,
            ..
        } => {
            popup.cycle_sort_key();
            (InputResult::None, true)
        }
        KeyEvent {
            code: KeyCode::Char('r'),
            modifiers: KeyModifiers::NONE,
            ..
        } => {
            popup.reverse_sort_direction();
            (InputResult::None, true)
        }
        KeyEvent {
            code: KeyCode::Esc, ..
        } => {
            self.dismissed_file_manager_token_range =
                Self::current_file_manager_token_range(&self.textarea);
            self.active_popup = ActivePopup::None;
            (InputResult::None, true)
        }
        KeyEvent {
            code: KeyCode::Tab, ..
        }
        | KeyEvent {
            code: KeyCode::Enter,
            modifiers: KeyModifiers::NONE,
            ..
        } => {
            match popup.activate_selected() {
                FileManagerSelection::SelectedFile(path) => {
                    self.insert_selected_file_manager_path(&path);
                    self.active_popup = ActivePopup::None;
                }
                FileManagerSelection::OpenedDirectory | FileManagerSelection::None => {}
            }
            (InputResult::None, true)
        }
        input => self.handle_input_basic(input),
    }
}
```

- [ ] **Step 6: Integrate sync ordering**

Update `sync_popups` so `/file` takes priority before command popup and before `@`/skill popups:

```rust
let file_manager_token_range = Self::current_file_manager_token_range(&self.textarea);
let file_token = Self::current_at_token(&self.textarea);
let skill_token = self.current_skill_token();

let allow_command_popup =
    file_manager_token_range.is_none() && file_token.is_none() && skill_token.is_none();
self.sync_command_popup(allow_command_popup);
```

After command popup handling, add:

```rust
if let Some(range) = file_manager_token_range {
    self.sync_file_manager_popup(range);
    return;
}
self.dismissed_file_manager_token_range = None;
```

Update the popup cleanup match:

```rust
if matches!(
    self.active_popup,
    ActivePopup::File(_) | ActivePopup::Skill(_) | ActivePopup::FileManager(_)
) {
    self.active_popup = ActivePopup::None;
}
```

Add:

```rust
fn sync_file_manager_popup(&mut self, range: std::ops::Range<usize>) {
    if self.dismissed_file_manager_token_range.as_ref() == Some(&range) {
        return;
    }

    if !matches!(self.active_popup, ActivePopup::FileManager(_)) {
        self.active_popup = ActivePopup::FileManager(FileManagerPopup::new());
    }
}
```

- [ ] **Step 7: Run integration tests**

Run:

```sh
cargo test -p codex-tui2 typing_file_token_opens_file_manager_popup_immediately esc_dismisses_file_manager_popup_without_immediate_reopen
```

Expected: both tests pass.

- [ ] **Step 8: Commit**

```sh
git add codex-rs/tui2/src/bottom_pane/chat_composer.rs
git commit -m "Open file manager from file token"
```

### Task 4: Full Verification And Cleanup

**Files:**
- Modify if needed: `codex-rs/tui2/src/bottom_pane/file_manager_popup.rs`
- Modify if needed: `codex-rs/tui2/src/bottom_pane/chat_composer.rs`

- [ ] **Step 1: Run formatter**

Run:

```sh
just fmt
```

Expected: command exits successfully. If it rewrites files, inspect `git diff`.

- [ ] **Step 2: Run full TUI2 tests**

Run:

```sh
cargo test -p codex-tui2
```

Expected: all `codex-tui2` tests pass. If snapshot files are generated, inspect `.snap.new` files before accepting or deleting them.

- [ ] **Step 3: Run scoped lint fixer**

Run:

```sh
just fix -p codex-tui2
```

Expected: command exits successfully. Inspect any edits with `git diff`.

- [ ] **Step 4: Run focused tests again after lint fixes**

Run:

```sh
cargo test -p codex-tui2 bottom_pane::file_manager_popup current_file_manager_token_range_detects_standalone_file_token insert_selected_file_manager_path_replaces_file_token_and_preserves_surrounding_text typing_file_token_opens_file_manager_popup_immediately esc_dismisses_file_manager_popup_without_immediate_reopen
```

Expected: all focused tests pass.

- [ ] **Step 5: Commit verification cleanup**

Only commit if formatting or linting changed files:

```sh
git add codex-rs/tui2/src/bottom_pane/file_manager_popup.rs codex-rs/tui2/src/bottom_pane/chat_composer.rs codex-rs/tui2/src/bottom_pane/mod.rs
git commit -m "Polish file manager picker"
```

If no files changed, do not create an empty commit.
