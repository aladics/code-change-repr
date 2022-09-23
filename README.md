# Code representation tools

## Prerequisites
Copy config_default.yaml to config.yaml and set the values accordingly.

## Datasets
### Method Embedding (Doc2Vec)
We use Doc2Vec to embed each method. To get the used model, perform the following steps:
1. Prepare a corpus from sufficient amount of flattened methods (for example `corpus_2kk.csv`)
2. Using `doc2vec.create_dictionary` create a dictionary, the config is stored as global variables in the script (_TODO: refactor this to config.yaml_). It will be used in the next step to filter the corpus before training doc2vec.
3. Train a doc2vec model using `doc2vec.train`.

### Code change
Generating a code change dataset is done through these steps:
1. Run the VIC generator tool get a file `all_method_changes.csv` containing all method changes and a `scores.txt` file with the relevance scores
2. Using `dataset.filter_introducing_changes`, filter `all_method_changes.csv` to get a file `vulnerabilities.csv` containing only methods that were in a file which had relevance score in `scores.txt`
3. Using `code_changes.create_dataset` create the xval dataset `xval.csv` using `all_method_changes.csv` as negative set (the script will remove duplicates) and `vulnerabilities.csv` as positive set. 
4. Using `code_changes.vectorize_dataset` vectorize the methods referenced in `xval.csv`. Use option `--mode` to generate _Simple_ and _ChangeTree_ representation

### Metrics
Generating a dataset with metrics is done through these steps:
1. Perform the first 3 steps of section _Code change_ to generate `xval.csv`
2. Get SourceMeter ready, and set the path in `conf/conf.yaml`'s sourcemeter section to the directory where sm_analzer.sh (script running AnalyzerJava then cleaning up the results folder) or the Dockerfile (TODO: upload to github) is. This directory also has to have a folder "input" and "results" (these are the folders which SM will use). 
3. Run `dataset.commit_scores`

## Evaluation
Using `eval.hyper_search`, with a source file `xval.csv` we can hyper tune the DWF models and get the best model's performance in f-mes, precision and recall. Configurations can be found in `conf/conf.yaml`.