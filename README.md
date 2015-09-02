# docker-image-cleaner
From all the pulled docker images remove keep only the N most recent images pulled

## Installation
* Clone repo
* It is adviced to use a virtualenv
* To setup a virtualenv

  ```bash
  $ virtualenv --clear --always-copy VIRTUALENV_NAME
  ```

* Install dependencies

  ```bash
  $ VIRTUALENV_NAME/bin/pip install -r requeriments.txt
  ```

* Run it with the same privileges as the docker client

  ```bash
  $ VIRTUALENV_NAME/bin/python di_cleaner.py --help
  ```
  
* Another way

  ```bash
  $ source VIRTUALENV_NAME/bin/activate
  $ ./di_cleaner --help
  ```
