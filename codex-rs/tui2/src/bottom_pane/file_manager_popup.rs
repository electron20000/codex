use std::cmp::Ordering;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::time::SystemTime;

use ratatui::buffer::Buffer;
use ratatui::layout::Constraint;
use ratatui::layout::Layout;
use ratatui::layout::Rect;
use ratatui::text::Line;
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
        self.state
            .ensure_visible(self.entries.len(), self.entries.len().min(MAX_POPUP_ROWS));
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
        _ => Ordering::Equal,
    }
}

impl WidgetRef for &FileManagerPopup {
    fn render_ref(&self, area: Rect, buf: &mut Buffer) {
        let [header_area, rows_area] =
            Layout::vertical([Constraint::Length(1), Constraint::Min(1)]).areas(area);
        Line::from(self.sort_label()).render_ref(
            header_area.inset(Insets::tlbr(0, 2, 0, 0)),
            buf,
        );

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
                    display_shortcut: None,
                    match_indices: None,
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;
    use std::path::PathBuf;
    use std::time::Duration;
    use std::time::SystemTime;

    fn entry(
        name: &str,
        kind: FileManagerEntryKind,
        modified_secs: Option<u64>,
    ) -> FileManagerEntry {
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

        sort_entries(
            &mut entries,
            FileManagerSortKey::Name,
            SortDirection::Ascending,
        );

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

        sort_entries(
            &mut entries,
            FileManagerSortKey::Date,
            SortDirection::Descending,
        );

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

        sort_entries(
            &mut entries,
            FileManagerSortKey::Type,
            SortDirection::Ascending,
        );

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
