# Portfolio maintenance

- Keep the production URL `https://jhyu-portfolio.netlify.app/`.
- Netlify builds and publishes pushes to `main` from this repository. Run `npm run build && npm run check:output` before pushing website changes.
- Edit project content in `src/data/projects.json` and profile information in `src/data/profile.json`. Project routes and filter counts are derived from the data.
- Preserve the current hierarchy: SMP and Mojo as featured projects; CBALLM, inflammation imaging, and DDI in the modeling/validation section; the DB-based RAG example last in the full list.
- Keep static output, small client JavaScript, lazy images, and opt-in video playback. Do not embed media as data URIs.
- Preserve distinctions between synthetic demonstrations, reanalysis of frozen results, and fresh real-data model training. Do not invent contributions, publication status, or performance claims.
- Reproduction packages in `evidence/` are independent of the website build. They must never run as part of a Netlify deployment.
- Keep private project source, real student records, credentials, and local environment files out of this public repository.
- Follow the established visual system in `DESIGN.md`; the user requested Impeccable and Taste guidance for design work.
