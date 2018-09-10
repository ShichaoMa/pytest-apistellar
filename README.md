# apistellar pytest测试插件

# INSTALL
```
pip install pytest-apistellar
```

# USEAGE
pytest-apistellar主要有两个功能：
- 后台启动一个web服务，来测试接口
- 通过配置文件来支持更强大的mock，增强pytest mock功能的可用性

### 如何启动一个web服务
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
### 如何mock数据
我们在测试目录下新建一个pytest.ini配置文件，输入：
```
[pytest]
mock_config_file =
    mock_test.json
mock =
    paas_star.Routing.from_etcd
    paas_star.Mongo.database_names
```
`mock_config_file`指定了一个mock配置文件，里面定义了要mock的对象及其属性的mock方式，如：
```json
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
`mock`定义了session mock marker， 在pytest启动时，只会运行一次。


除了上面讲的session作用域下的mock以外，pytest-apistellar还支持module、class、function作用域下的mock，用法如下：
#### module作用域，以module作为namespace，在当前module定义全局变量pytestmark
```python
pytestmark = [pytest.mark.mock("paas_star.Routing.from_etcd", db="emp")]
```
#### class作用域，以class作为namespace，定义类变量pytestmark
```
class TestMimetype:
    pytestmark = [pytest.mark.mock("paas_star.Routing.from_etcd")]
```
#### function作用域，每个单元测试都会加载一次，使用mark来标注
```
@pytest.mark.mock("paas_star.Routing.from_etcd", db="emp")
@pytest.mark.mock("uploader.uploader.mimetype.repository.MimetypeRepository.get_mimetypes")
@pytest.mark.usefixtures("mock")
@pytest.mark.asyncio
async def test_mimetype(server_port):
    url = f"http://localhost:{server_port}/mimetype/"
    async with ClientSession(conn_timeout=10, read_timeout=10) as session:
        resp = await session.get(url)
        data = await resp.json()
        assert isinstance(data, list)
```
pytest.mark.mock可以指定关键字参数如`db="emp"`，当该mock返回值配置为一个工厂时，
该工厂会接收到`db=emp`字样的关键字参数，一般用来个性化不同场景下同一个mock的行为。

最后，定义了作用域不代表mock会生效，要mock生效还需要指定`@pytest.mark.usefixtures("mock")`才可以