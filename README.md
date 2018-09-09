# apistellar 测试插件

在test目录下编写名为mock.json的配置文件用来mock一些对象的的方法或属性
```
{
 "mocks": [
   {"obj": "paas_star.Mongo",
    "props": [
          {"name": "find_one",
           "async": true,
           "ret_val": null,
           "ret_factory": "factories.MongoFactory",
           }
        ]
    }
 ]
}
```