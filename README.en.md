# vippool-clerk

This application, meant to be run on Google App Engine,
helps to get data and to create transactions on the blockchain.

## Features

All the block data and transaction data that can be obtained by a coin node RPC
are stored and synced in a relational database (RDB)
so that you can retrieve them in JSON easily from there.

Block data and transaction data provide only a reference to past data,
but there are no references for the next events.
vippool-clerk stores and returns this kind of information, which is quite useful.

Moreover, all changes in the account balance of each coin address are recorded.
It is then possible, for example, to develop an account book application,
that would show this information to users.

And we provide a tool to help create transactions.
There are two stages in transaction creation:
1. the API is called a first time and returns a hash, which is then, on the client side, signed by ECDSA.
2. and the API is called again, then the transaction is complete.

Thus, the electronic signature is happening on the client side,
reducing the risk of compromission of the private key.

## API usage

About the public API, please refer to the manual included in [doc/api.md](doc/api.md).

## Installing

Before installing you need to make sure you have the following prerequisites:
1. Google App Engine account
2. Google Cloud SQL server
3. coin node server (that may be launched on Google Compute Engine)

First, we need to launch one instance of the coin node server.
Please add the following line to the node server's "conf" file:
> server=1  
> rpcuser=xxxxx  
> rpcpassword=xxxxx  
> rpcport=xxxx  
> rpcallowip=0.0.0.0/0  
> txindex=1

rpcallowip is required because Google App Engine does not know how to get to the server.
By creating a virtual network, we can limit ourselves to local IP addresses.
txindex=1 indicates that we want to get the data for all of the transactions.

After that, we need to parametrize Google Cloud SQL.
First, launch the MySQL server. You can leave the default settings,
but it may be better to adjust it to your liking, for performance optimization, etc.
You don't need to prepare in advance the database, as it will be created automatically.
Then create database user for Google App Engine to access the MySQL.

Then, let's edit server/config.py.
It is empty by default, so you need to fill in the same password, etc. than in the first step. 

Finally, we deploy the project on Google App Engine.
There is an order to respect, so please proceed as explained below:
> gcloud app deploy app.yaml  
> gcloud app deploy queue.yaml  
> gcloud app deploy cron.yaml

TaskQueue sends sync requests from cron, and thus the synchronization is done regularly.

You can even use it for other altcoins.
However, if you change the node server, you may need to make a few modifications.

## Contact

For asking for information, request features, or submit bug reports; please use the Github "issues" page.  
https://github.com/vippool/clerk/issues

You can also send an email to our developers:  
dev-team@vippool.net

## License

(C) 2019-2019 VIPPOOL Inc.

This project is published under the MIT license.
