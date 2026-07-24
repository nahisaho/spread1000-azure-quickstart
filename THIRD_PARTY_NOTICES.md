# Third-Party Notices

This quickstart collection references and depends on the following third-party components. Each carries its own license terms; consult the linked upstream project for the authoritative text.

## Runtime dependencies (Python)

| Package | License | Upstream |
|---|---|---|
| `gplearn` | BSD-3-Clause | https://gplearn.readthedocs.io/ |
| `openai` | Apache-2.0 | https://github.com/openai/openai-python |
| `azure-identity` | MIT | https://github.com/Azure/azure-sdk-for-python |
| `azure-ai-documentintelligence` | MIT | https://github.com/Azure/azure-sdk-for-python |
| `azure-ai-ml` | MIT | https://github.com/Azure/azure-sdk-for-python |
| `azure-storage-blob` | MIT | https://github.com/Azure/azure-sdk-for-python |
| `pydantic` | MIT | https://github.com/pydantic/pydantic |
| `python-dotenv` | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| `scikit-learn` | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn |
| `numpy` | BSD-3-Clause | https://numpy.org/ |
| `pandas` | BSD-3-Clause | https://pandas.pydata.org/ |
| `umap-learn` | BSD-3-Clause | https://github.com/lmcinnes/umap |
| `xgboost` / `xgboost-cpu` | Apache-2.0 | https://xgboost.readthedocs.io/ |
| `pymatgen` | MIT | https://pymatgen.org/ |
| `matminer` | BSD-3-Clause | https://hackingmaterials.lbl.gov/matminer/ |
| `mp-api` (Materials Project) | BSD-3-Clause | https://github.com/materialsproject/api |
| `torch` | BSD-3-Clause | https://pytorch.org/ |
| `matplotlib` | PSF-based | https://matplotlib.org/ |
| `biopython` | BSD-3-Clause-like | https://biopython.org/ |
| `rdkit` | BSD-3-Clause | https://www.rdkit.org/ |
| `SudachiPy` / `SudachiDict-core` | Apache-2.0 | https://github.com/WorksApplications/SudachiPy |
| `reportlab` | BSD-3-Clause | https://www.reportlab.com/ |
| `Pillow` | HPND | https://python-pillow.org/ |

Exact versions used per scenario are pinned in each scenario's `requirements-lock` directory.

## Models and datasets

Third-party models and datasets referenced by individual scenarios (each carries its own license — verify before redistribution):

- **PBMC3k dataset (10x Genomics)** — CC BY 4.0; Zheng et al. (2017) Nat Commun DOI 10.1038/ncomms14049; source page https://support.10xgenomics.com/single-cell-gene-expression/datasets/1.1.0/pbmc3k; Scanpy 1.10+ fetches converted H5AD from falexwolf.de.
- **scanpy** — see https://github.com/scverse/scanpy (BSD-3-Clause).
- **python-igraph** — see https://igraph.org/python/ (GPL-2.0).
- **Azure OpenAI hosted models** — subject to the Microsoft Product Terms and Azure OpenAI Service terms.
- **BioEmu** — see https://github.com/microsoft/bioemu (MIT).
- **ESMFold / ESM-2** — see https://github.com/facebookresearch/esm (MIT).
- **AlphaFold3** — see https://github.com/google-deepmind/alphafold3 (CC-BY-NC-SA-4.0 for the source; model weights subject to separate DeepMind terms).
- **TamGen** — see https://github.com/microsoft/TamGen (MIT).
- **REINVENT4** — see https://github.com/MolecularAI/REINVENT4 (Apache-2.0).
- **ReactionT5** — see https://github.com/sagawatatsuya/ReactionT5v2 (MIT).
- **MACE / mace-mp-0** — see https://github.com/ACEsuit/mace (MIT); mace-mp-0 weights on Hugging Face.
- **MONAI Model Zoo bundles** — see https://monai.io/model-zoo.html for per-bundle license.
- **Materials Project (via `mp-api`)** — data licensed CC-BY-4.0; consult https://next-gen.materialsproject.org/about/terms.
- **QM9, ESOL, MoleculeNet, ChEMBL** — cite the upstream dataset publications and consult the redistribution terms of the specific dataset source used.
- **PTB-XL / MIT-BIH** — PhysioNet Credentialed Health Data License; obtain access via https://physionet.org/.
- **UK Biobank** — restricted access; consult UK Biobank Access Procedures.
- **MIMIC-IV** — PhysioNet Credentialed Health Data License 1.5.0.
- **ColabFold parameters** — subject to the ColabFold and AlphaFold2 terms.
- **Microsoft GraphRAG** — see https://github.com/microsoft/graphrag (MIT).
- **GNoME dataset** — CC-BY-NC-4.0; not redistributed in this repository.

## Notes

- This file is a best-effort summary and is not legal advice. When redistributing derivatives that include any of the above, verify current upstream licenses.
- The synthetic datasets shipped under `research-fields/*/data/` are CC0-1.0 (see `data/LICENSE`).
- Source code and prose in this repository (excluding third-party components above) is MIT — see the repository-root `LICENSE`.
