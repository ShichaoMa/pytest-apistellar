# apistellar pytest测试插件

# INSTALL
```
pip install pytest-apistellar
```

# USEAGE
pytest-apistellar主要有两个功能：
- 后台启动一个web服务，来测试接口
- 使用装饰器增强pytest mock功能的可用性，目前支持属性和环境变量的mock

## 如何启动一个web服务
下面的代码在定义了server参数后自动使用子线程启动了一个ASGI server
```python
@pytest.mark.asyncio
async def test_mimetype(server):
    url = f"http://localhost:{server.port}/mimetype/"
    async with ClientSession(conn_timeout=10, read_timeout=10) as session:
        resp = await session.get(url)
        data = await resp.json()
        assert isinstance(data, list)
```
如何将我们定义的Controller挂到这个server中呢？我们知道apistellar拥有自动发现功能，只要Controller被加载过就会自动注册到路由表中，所以通过导包或者直接将要测试的Controller定义在test文件中即可。如：
```python
from uploader.uploader.mimetype import MimetypeController
```
一个api单元测试就写好了，可以直接使用pytest命令启动
## 如何mock属性, 环境变量, 字典, 工作目录, python包搜索路径
### mock属性
除了全局的mock以外，mock使用pytest.mark.prop来实现。
pytest.mark.prop可以被传递入位置参数和关键字参数，具体用法如下：
- args[0]: 第一个位置参数，指定被mock的对象或方法，使用`model.class.method`样式的字符串指定。
- ret_val: 关键字参数，指定被mock的方法的返回值或者被mock的属性的值。
- ret_factory: 关键字参数，指定一个工厂(可调用对象)，其返回值将作为被mock的方法的返回值或者被mock的属性的值，与ret_val二者指定其一。
- asyncable: 关键字参数，被mock的方法或函数是否是异步的，通常可以忽略这个参数，因为插件会自动猜测其性质，但是有些同步的函数会返回future来伪装成异步函数，这时需要指定。
- callable: 关键字参数，这个在特定情况下需要指定，比如要mock一个属性，但属性是可调用的，此时要传callable=False。
- fixture_inject: 关键字参数，ret_factory是否使用fixture的注入机制，默认为False。
- args[1:]: 其它位置参数会被作为ret_factory的参数传入。
- kwargs: 其它关键字参数会被作为ret_factory的参数传入。

pytest-apistellar支持session, module、class、function作用域下的mock。

#### session作用域
session作用域下的mock全局有效。

我们新建一个pytest.ini配置文件，输入：
```ini
[pytest]
prop =
    paas_star.Routing.from_etcd->factories.RoutingFactory
    uploader.uploader.s3.file.File.TABLE="test_file"
```
每行为一个mock

- 第一个mock

args[0] = paas_star.Routing.from_etcd

ret_factory = factories.RoutingFactory

- 第二个mock

args[0] = uploader.uploader.s3.file.File.TABLE

ret_val = "test_file"

ret_val的获取手段是执行eval()同时传入=后面的数据，如果=号后面的数据是需要导包的，框架还会进行自动导包。

#### module作用域
module作用域的mock仅在当前模块有效，在当前模块定义全局变量pytestmark
```python
pytestmark = [pytest.mark.prop("uploader.uploader.s3.repository.S3Repository.mongodb", ret_factory="factories.mongo_factory")]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.prop("uploader.uploader.s3.repository.S3Repository.mongodb", ret_factory="factories.mongo_factory")]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.prop("uploader.uploader.s3.repository.S3Repository.mongodb", ret_factory="factories.mongo_factory")
@pytest.mark.usefixtures("mock")
@pytest.mark.asyncio
async def test_mimetype(self, server_port):
    url = f"http://localhost:{server_port}/mimetype/"
    async with ClientSession(conn_timeout=10, read_timeout=10) as session:
        resp = await session.get(url)
        data = await resp.json()
        assert isinstance(data, list)
```
我们可能对过长的装饰器感到困惑，pytest-apistellar提供了别名支持
```python
s3_repo = prop_alias("uploader.uploader.s3.repository.S3Repository")
s3_file = prop_alias("uploader.uploader.s3.file.File")
bkd_s3 = prop_alias("paas_star.backend.s3.dummy_s3", mock_factory_prefix="fac")
fairyland = prop_alias("uploader.uploader.s3.fairyland.Fairyland")

```
指定mock_obj_prefix和mock_factory_prefix，就不必写过长的模块名了。在定义好别名后，直接使用别名装饰器，和pytest.mark.prop没有任何区别
```python
pytestmark = [
        s3_repo("mongodb", ret_factory="mongo_factory"),
        s3_repo("s3", ret_factory="s3_factory"),
        s3_repo("settings", ret_factory="settings_factory"),
        s3_repo("session", ret_factory="session_factory"),
        s3_file("save", ret_val={"ok": 1}),
        s3_file("mongo", ret_factory="mongo_factory"),
        bkd_s3("Bucket.delete_key"),
        bkd_s3("Key.set_contents_from_file",
                   ret_factory="set_contents_from_file_factory"),
        bkd_s3("Key.set_canned_acl"),
        bkd_s3("Key.get_contents_as_string",
                   ret_factory="download_from_s3",
                   fn="download_data")
    ]
```
### mock环境变量
mock 环境变量和mock属性类似。
#### session作用域
在pytest.ini中增加
```ini
[pytest]
env =
    APP_NAME=123
    APP_TARGET=preview
```
环境变量=号两边不能有空格
#### module作用域
以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.env(APP_NAME="123")]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.env(APP_NAME="123")]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.env(APP_NAME="TEST")
@pytest.mark.usefixtures("mock")
def test_appname(self):
    import os
    assert os.getenv("APP_NAME") == "TEST"
```

### mock字典

#### session作用域
在pytest.ini中增加
```ini
[pytest]
item =
    factories.data["a"]=11
```
factories.data指向一个字典属性
#### module作用域
以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.item(data, a=2)]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.item(data, a=3)]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.item(data, a=4)
@pytest.mark.usefixtures("mock")
def test_appname(self):
    assert data["a"] == 4

### mock工作目录

#### session作用域
在pytest.ini中增加
```ini
[pytest]
path =
    ../
```
可以使用绝对路径和相对路径
#### module作用域
以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.path("../")]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.path("../")]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.path("../")
@pytest.mark.usefixtures("mock")
def test_appname(self):
    ...


### mock python搜索路径

#### session作用域
在pytest.ini中增加
```ini
[pytest]
syspath =
    ../
```
可以使用绝对路径和相对路径
#### module作用域
以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.syspath("../")]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.syspath("../")]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.syspath("../")
@pytest.mark.usefixtures("mock")
def test_appname(self):
    ...

## ret_factory配合fixture_inject使用
设置fixture_inject=True，可以为ret_factory指定fixture，以对同一个单元测试mock不同的数据来多次执行。
由于fixture是在mock时完成注入的，所以fixture的scope不能使用function
```python
import pytest


@pytest.fixture(scope="session", params=[x for x in range(1, 5)])
def a(request):
    return request.param


pytestmark = [
    pytest.mark.prop("factories.TestClass.get_data_module",
                     ret_factory=lambda a, **kwargs: a * 3, fixture_inject=True)
]


@pytest.mark.prop("factories.TestClass.get_data_class",
                     ret_factory=lambda a, **kwargs: a * 4, fixture_inject=True)
class TestPropPatcher(object):

    @pytest.mark.prop("factories.TestClass.get_data_function",
                     ret_factory=lambda a, **kwargs: a * 5, fixture_inject=True)
    def test_factory(self, a):
        from factories import TestClass
        assert TestClass.get_data_function() == a * 5
        assert TestClass.get_data_class() == 4
        assert TestClass.get_data_module() == 3

```
## 最后
定义了mock配置并指定了作用域不代表mock会生效，要mock生效还需要指定`@pytest.mark.usefixtures("mock")`才可以。
