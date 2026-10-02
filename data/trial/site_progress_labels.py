"""By-eye labels for the Site Progress trial (data/trial/site_progress_trial.py). Empty until read.

Open data/build/site_progress_sheet.html (or the photo paths in results/site_progress_sample.csv)
and, for each sampled photo, write what YOU see, not what the engine read:

  PHOTO_LABELS[file id] = "shows"      the finished asset of the work's type is plainly in it
                          "not_built"  the place is in it and the asset plainly is not (bare
                                       ground, foundations, walls without a roof, a dirt track)
                          "cant_tell"  anything else (too far, a document, people, another thing)

  WORK_LABELS[work id]  = "yes"  the engine's finding is worth a site check
                          "no"   it is not (say why in a comment)

Describe works by their work id only, never by a person's name (AGENTS.md rule 6).
"""

PHOTO_LABELS: dict[str, str] = {}

WORK_LABELS: dict[str, str] = {}
