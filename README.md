python-echonet-lite
===================

これはなに？
------------

ECHONET Lite機器を持っていない私が [Kadecot][] を試すために作った、
[ECHONET Lite][] プロトコルのPure Python実装です。

使い方
------

main.py

    import echonet_lite
    
    node = echonet_lite.Node()
    node.add_object(echonet_lite.GeneralLighting())
    node.loop(debug=True)

echonet_lite.GeneralLighting クラスのように、
echonet_lite.Object クラスを継承してservice関数を実装すれば、
任意のECHONETオブジェクトを実装できるかもしれません。

進捗
----

2014/10/13 ひとまずKadecotが認識するところまで。

License
-------

Copyright 2014 Keisuke Minami

Apache License 2.0


[ECHONET Lite]: http://www.echonet.gr.jp/ "ECHONET Lite"
[Kadecot]: http://kadecot.net/ "Kadecot"

