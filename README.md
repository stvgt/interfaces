# Interfaces
Service for managing interfaces, their consumers and producers.

# Problem to be solved

When coping with microservices, often the question arises, how the
services depend on each other. From the perspective of a producer
it is interesting, which parts in the interface are in use.

The service solves the problem by managing which interfaces are used.
It can be any interfaces: http calls, events, shared files, shared tables.

# Problem not to be solved

The service does not manage how the interfaces are used, e.g. which
individual fields of a rest response are required by consumers like
Consumer-Driven Contracts do.
But knowing the consumers can also support answering this question.

# How it works

- The individual components, e.g. services, contain a declaration of
which interfaces they consume and produce by means of a config file.
- A centralized server keeps book of the individual interfaces of the
components.
- The components send their interface description to the server, e.g.
using curl as part of the ci/cd.
- The server responds whether the change is possible (200) or not (409).

- TO BE DONE: The server also provides a list of interfaces. This is
used to visualize the whole dependency graph or just a filtered subset.

## Example

**Request:** I am Alice. I produce milk.
**Response:** OK: I stored this about you, Alice.

**Request:** I am Bob. I consume milk and water.
**Response:** Conflict: No one produces water.

**Request:** I am Carol. I produce water.
**Response:** OK: I stored this about you, Carol.

**Request:** I am Bob. I consume milk and water.
**Response:** OK: I stored this about you, Bob.

**Request:** I am Alice. I produce tea.
**Response:** Conflict: You are the only one producing milk. Milk is used.

# Requirements

- A postgres database
- Infrastructure to run the service

# Setup

## Central Service
- Create a database + user to access.
- Create once the respective tables 
(see [service/database/initialization_queries.py](service/database/initialization_queries.py))
- Deploy the service, e.g. using uwsgi.
  - Flask entrypoint is [service/app.py:app](service/app.py)
  - Environment variables to configure service:
    - POSTGRES_DB_HOST, default = 'localhost'
    - POSTGRES_DB_PORT, default = '5432'
    - POSTGRES_DB_NAME, default = 'interfaces'
    - POSTGRES_DB_USER, default = 'postgres'
    - POSTGRES_DB_PASS, default = 'postgres'
- Swagger: [http://127.0.0.1:5000/api](http://127.0.0.1:5000/api)

## Interface description per service
### Create a yaml file containing interface declaration.
Example: [test/testdata/mixed.yaml](test/testdata/mixed.yaml)
- Global fields:
  - sub-component: optional, name of sub component
- shared consumer and producer fields:
  - host: the host of the provider, e.g. a service name
  - type: the type of the provider, e.g. 'rest'
  - values/primary, values/secondary, values/tertiary: the interface, split in parts. Default = ""
- consumer fields:
  - values/optional: if set to true, then the interface is not enforced. Default = false
- producer fields:
  - values/deprecated: sets the interface to deprecated. No effect on interface enforcement. Default = false
- Constraints:
  - unique (sub-component, host, type, values/primary, values/secondary, values/tertiary)

=> The file provides lots of flexibility.
It is not given that the http method is stored as primary as in the examples.
So it is important to define how to use the individual fields before one starts.

### Use curl to upload the file in a build step. Example
- component = "my_component"
- declaration filename: "interface.yaml"
- call: ` curl -X PUT "http://127.0.0.1:5000/api/v1/components/my_component/interfaces/yaml" -H  "accept: application/json" -H  "Content-Type: multipart/form-data" -F "yaml_file=@interface.yaml"
`
  