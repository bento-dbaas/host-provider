[![Build Status](https://travis-ci.com/bento-dbaas/host-provider.svg?branch=master)](https://travis-ci.com/bento-dbaas/host-provider) [![codecov](https://codecov.io/gh/bento-dbaas/host-provider/branch/master/graph/badge.svg?token=GQN1ZN9FJQ)](https://codecov.io/gh/bento-dbaas/host-provider)


## Host Provider

### How to run

#### Native:
 - Copy the base env file to dev env file:
```shell
$cp .export-host-provider-local-base.sh .export-host-provider-local-dev.sh
```
 - Replace variables in `.export-host-provider-local-dev.sh` file.
 - install requirements:
  ```shell
 $pip install -r requirements.txt
 ```
 - load environment variables:
  ```shell
$source .export-host-provider-local-dev.sh
  ```

 - run project: `$make run`

#### Docker Compose:
`todo`

### Configure DBaaS:
Go to your `DBaaS local instance > DBaaaS_Credentials > Credentials` and point the `Host Provider` Cretentials to your host provider instance (127.0.0.1:5002)

### Setup MySQL Database

#### Initialize Script
```shell
$make db_initialize
```

#### Schema Migration
```shell
$make db_migrate
```