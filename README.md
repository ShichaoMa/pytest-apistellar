# apistellar pytest测试插件

# INSTALL
```
pip install pytest-apistellar
```

# USEAGE
pytest-apistellar主要有两个功能：
- 后台启动一个web服务，来测试接口
- 通过配置文件来支持更强大的mock，增强pytest mock功能的可用性，目前支持属性和环境变量的mock

## 如何启动一个web服务
下面的代码在定义了server_port参数后自动使用子线程启动了一个ASGI server
```python
@pytest.mark.asyncio
async def test_mimetype(server_port):
    url = f"http://localhost:{server_port}/mimetype/"
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
## 如何mock属性和环境变量
### mock属性
#### mock配置
我们在启动pytest时指定参数： --mock-config-file=mock.json,
`mock.json`指向mock的配置文件，里面定义了要mock的对象及其属性的mock方式，如：
```js
{
 "mocks": [
   {"obj": "paas_star.Routing", // 要mock的对象
    "props": [
          {"name": "from_etcd", // 该对象属性(方法)名
           "ret_factory": "factories.RoutingFactory" // 使用一个工厂来代替from_etcd。
           }
        ]
    },
   {"obj": "uploader.uploader.mimetype.repository.MimetypeRepository",
    "props": [
          {"name": "get_mimetypes",
           "ret_val": ["zip/application"] // 不使用工厂，直接给定一个返回值
           }
        ]
    },
   {"obj": "paas_star.Mongo",
    "props": [
          {"name": "database_names",
           "ret_val": ["emperor"]}
        ]
    }
 ]
}
```
同时mock配置文件还支持yaml格式，以便使配置更加简洁。

#### 使用配置好的mock

##### 全局的mock
我们新建一个pytest.ini配置文件，输入：
```ini
[pytest]
prop =
    paas_star.Routing.from_etcd
    paas_star.Mongo.database_names
```
使用pytest.ini配置的mock默认是全局的(session)，只会在测试启动时执行一次。

##### 其它作用域的mock
除了上面讲的session作用域下的mock以外，pytest-apistellar还支持module、class、function作用域下的mock，用法如下：
##### module作用域
以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.prop("paas_star.Routing.from_etcd", db="emp")]
```
###### class作用域
以class作为namespace，定义类变量pytestmark
```python
class TestMimetype:
    pytestmark = [pytest.mark.prop("paas_star.Routing.from_etcd")]
```
###### function作用域
每个单元测试都会加载一次，使用mark来标注
```python
@pytest.mark.prop("paas_star.Routing.from_etcd", db="emp")
@pytest.mark.prop("uploader.uploader.mimetype.repository.MimetypeRepository.get_mimetypes")
@pytest.mark.usefixtures("mock")
@pytest.mark.asyncio
async def test_mimetype(self, server_port):
    url = f"http://localhost:{server_port}/mimetype/"
    async with ClientSession(conn_timeout=10, read_timeout=10) as session:
        resp = await session.get(url)
        data = await resp.json()
        assert isinstance(data, list)
```
pytest.mark.mock可以指定关键字参数如`db="emp"`，当该mock返回值配置为一个工厂时，
该工厂会接收到`db=emp`字样的关键字参数，一般用来个性化不同场景下同一个mock的行为。
### mock环境变量
mock 环境变量和mock属性类似，不过不需要使用mock配置文件
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
## 最后
定义了mock配置并指定了作用域不代表mock会生效，要mock生效还需要指定`@pytest.mark.usefixtures("mock")`才可以。
