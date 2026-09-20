# Maintaining documentation and the wiki

The active documentation source is `docs/` in the main repository. GitHub Pages serves it with Docsify. The native build, migration, audit, validation and release notes remain authoritative under `native/` and are mirrored into the site by a checked generator.

## Updating pages

Edit authored guides in `docs/`. For generated module pages, update `native/MODULE_AUDIT.md`; module IDs and defaults must match `native/src/engine.cpp`. For generated build/migration/validation/release pages, edit the corresponding `native/*.md` source. Then run:

```sh
python native/tools/sync-docs.py
python native/tools/sync-docs.py --check
```

The check verifies generated content, module coverage/defaults, navigation, active local Markdown links and documented command names. It does not replace native or gameplay validation. For site navigation changes, serve `docs/` locally and check Docsify routes/search in a browser. Historical Python documents are explicitly archived and excluded from active checks.

## Publishing the separate GitHub wiki

GitHub requires the first wiki page to exist before its separate Git repository can be cloned. Create a Home page through GitHub once if the wiki has never been initialized. See [GitHub's wiki instructions](https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages).

After initialization, clone the wiki into the ignored scratch directory and export the current site pages:

```sh
git clone https://github.com/TheNINJALLO/endstone-paradox.wiki.git scratch/paradox-wiki
python native/tools/sync-docs.py --check --wiki-output scratch/paradox-wiki
```

Review the wiki diff, commit it and push its current branch. The exporter flattens module/command page names, rewrites links, and generates Home, a sidebar and a footer. It writes Markdown only and never deletes other wiki files. Its output can also be prepared in an empty directory before GitHub initialization.

Commit and push main for the documentation site. GitHub Pages deployment is separate from native binary releases; documentation-only changes do not alter the v2.0.1 tag or published plugin packages.
