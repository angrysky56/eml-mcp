# Phase Context: SQLite Persistence Layer

## Design Decisions

- **Database Location**: The database file `eml_formulas.db` will be located in the repository root directory. This provides easy access and simple integration for development and usage. We will ensure the database file is added to `.gitignore`.
- **Serialization**: The `EMLNode` tree structures and properties like `rpn` will be serialized as JSON strings within text columns. This allows us to handle recursive nested structures simply without the overhead of schema normalization, perfectly leveraging the standard `json` module.
- **Access Pattern**: We will use the raw `sqlite3` module from the Python standard library, utilizing `sqlite3.Row` for dict-like access. This fully satisfies the zero-dependency requirement while providing robust row interaction.

## Open Areas

- No remaining gray areas. The DB schema and implementation path are clear.
