import echonet_lite

node = echonet_lite.Node()
node.add_object(echonet_lite.GeneralLighting())
node.loop(debug=True)

