**This branch (TF2) is an attempt to port Grover to Tensorflow 2 and Keras.**

tf_upgrade_v2 script has been run (https://www.tensorflow.org/guide/upgrade) with results in report.txt

Due to file sizes, models and checkpoints are not included. please refer to original documentation, excerpts below.

**Download the models**

"python download_model.py [base | large | mega]"

These are copied to "models" top level directory, in "base", "large", and "mega" subdirectories.

**Discrimination checkpoints**

Medium trained on medium, top-p=0.96:
```
gs://grover-models/discrimination/generator=medium~discriminator=grover~discsize=medium~dataset=p=0.96/model.ckpt-1562.data-00000-of-00001
gs://grover-models/discrimination/generator=medium~discriminator=grover~discsize=medium~dataset=p=0.96/model.ckpt-1562.index
gs://grover-models/discrimination/generator=medium~discriminator=grover~discsize=medium~dataset=p=0.96/model.ckpt-1562.meta
```

Mega trained on mega, top-p=0.94:
```
gs://grover-models/discrimination/generator=mega~discriminator=grover~discsize=mega~dataset=p=0.94/model.ckpt-1562.data-00000-of-00001
gs://grover-models/discrimination/generator=mega~discriminator=grover~discsize=mega~dataset=p=0.94/model.ckpt-1562.index
gs://grover-models/discrimination/generator=mega~discriminator=grover~discsize=mega~dataset=p=0.94/model.ckpt-1562.meta
```

