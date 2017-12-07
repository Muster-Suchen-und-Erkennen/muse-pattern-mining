# Help for mining_model_creator.py

## usage:

__Requires Python >= 3.3__

For better hashes install `humanhash3` or another version of `humanhash`:

```
pip install humanhash3
```


```bash
python3 mining_model_creator.py -h
```

### 0. make a mining model with all available mining columns.

### 1. extract mining columns from model:

```bash
python3 mining_model_creator.py extract <name of mining model>
```

Where `<name of mining model>` is the filename of the mining model. The tool searches all nested folders for the mining model.

The generated `<name of mining model>.csv` looks like this:

```csv
;Basiselement;Genre;Beruf
Basiselement;;;
Genre;;;
Beruf;;;
```

### 2. define the models to create:

|              | Basiselement | Genre | Beruf  |
|--------------|:------------:|:-----:|:------:|
| Basiselement |              | x     |  x     |
| Genre        |              |       |        |
| Beruf        |              | x     |        |


```csv
;Basiselement;Genre;Beruf
Basiselement;;x;x
Genre;;;
Beruf;;x;
```

The first row defines all possible input columns. The first name of the following rows defines column to predict. Every non empty cell is regarded as true.


### 3. create the models:

```bash
python3 mining_model_creator.py create <name of csv-file>
```

This will create one model for every non empty cell.

To create models with multiple input columns use:

```bash
python3 mining_model_creator.py create --multiple-input-columns <name of csv-file>
# or
python3 mining_model_creator.py create -m <name of csv-file>
```

This will create one model for every row. You can copy a row to make different models predicting the same mining column.
Ìf the generated name exceeds 100 characters in length the input columns get replaced by a hash. For human readable hashes please install `humanhash`.  If a column with name `filename` is present in the csv, than the filename is read from this column.

You can also specify the mining model to use as base for model creation:

```bash
python3 mining_model_creator.py create --model <name of mining model> <name of csv-file>
```

## What if i make a mistake in the csv file?

You can delete all created models with:

```bash
python3 mining_model_creator.py delete <name of csv-file>
```

This relies entirely on filenames!!!


## What if i execute a command more than once?

The tool asks if a file alredy exists.


## What if i changed a model and accidentally deleted it with the tool?

Commit changes __before__ using the tool!!!

