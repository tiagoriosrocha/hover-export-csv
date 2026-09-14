# HoVer pronto para grafos

Este projeto converte o dataset [HoVer](https://hover-nlp.github.io/) em CSVs
para experimentos de grafos. O HoVer fornece a claim, o rótulo e as referências
das sentenças de evidência; este projeto resolve o texto dessas sentenças no
corpus Wikipedia oficial processado pelo HotpotQA.

## Pré-requisitos

- Python 3.10 ou superior;
- acesso à internet no primeiro uso;
- espaço livre suficiente para baixar e extrair o corpus HotpotQA. O download
  tem aproximadamente 7,4 GB e a extração exige espaço adicional.

O pipeline usa somente a biblioteca padrão do Python, portanto não há pacotes
extras para instalar.

## Como executar

No macOS ou Linux:

```bash
python3 -m venv .venv
.venv/bin/python run.py
```

No Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe run.py
```

O `run.py` é multiplataforma e faz o fluxo completo:

1. baixa os splits oficiais de treino, desenvolvimento e teste do HoVer quando
   estiverem ausentes;
2. baixa e extrai o corpus Wikipedia processado pelo HotpotQA quando necessário;
3. executa `export_graph_ready_csv.py`.

Os arquivos baixados ficam em `data/`, que é ignorada pelo Git. Em execuções
seguintes, arquivos já existentes são reutilizados.

## Saídas

Após a exportação, `processed-data/` contém:

```text
processed-data/
├── train.csv
├── dev.csv
└── hover_dataset_full.csv
```

O split de teste do HoVer contém somente claims, sem rótulos ou evidências;
por isso não participa dos CSVs prontos para grafos.

Cada linha dos CSVs exportados tem as colunas:

```text
id,label,split,claim,evidence_text,evidence,evidence_annotation_id,
evidence_id,evidence_wiki_url,evidence_sentence_id
```

Os campos de evidência são JSON válido dentro da célula CSV. `evidence_text`
usa o formato `[{"set_id": 0, "text": ["sentença 1", "sentença 2"]}]`.
As sentenças correspondem aos fatos de suporte anotados no HoVer.

Algumas anotações apontam para uma posição inexistente no snapshot do corpus
HotpotQA. Esses exemplos não são incluídos nos CSVs para não associar uma
evidência incorreta ao claim; o arquivo `unresolved_evidence.csv` registra os
casos e os índices que não puderam ser resolvidos.

## Arquivos do projeto

- `run.py`: download, verificação e execução do pipeline;
- `export_graph_ready_csv.py`: conversão das anotações e resolução das
  evidências;
- `requirements.txt`: intencionalmente sem dependências externas;
- `.gitignore`: impede que o corpus baixado e os CSVs gerados sejam enviados ao
  Git.
