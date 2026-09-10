# HoVer pronto para grafos

O projeto exporta claims HoVer e suas evidências no esquema CSV do FEVEROUS.
As anotações HoVer guardam título e índice de sentença; o texto é resolvido no
corpus Wikipedia oficial processado pelo HotpotQA.

```bash
python -m venv .venv
.venv/bin/python run.py
```

No Windows, execute `.venv\\Scripts\\python.exe run.py`.

No primeiro uso, `run.py` baixa as anotações HoVer e o corpus HotpotQA (~7,4
GB), extrai o corpus e gera `processed-data/train.csv`,
`processed-data/dev.csv` e `processed-data/hover_dataset_full.csv`.
