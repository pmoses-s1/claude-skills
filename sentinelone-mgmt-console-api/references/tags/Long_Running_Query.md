# Long Running Query

3 endpoints.

## `POST /sdl/v2/api/queries`
**Launch a query**
`operationId`: `_sdl_v2_api_queries_post`

Returns a `QueryResult` containing the query identifier, status, and, if the query completes immediately, the full result set in the `data` field. If the query is still processing, the `data` field will be null. Use the returned query id to poll the query via GET `/v2/api/queries/{id}` until results are available. The API rate limit is 100 requests per second. Log queries have a default limit of 1000 events but by paginating can be used to return essentially unlimited results. Power query results are subject to the standard power query limits on row count and memory consumption. A successful response will also include a X-Dataset-Query-Forward-Tag header that must be applied to the subsequent Poll and Delete requests for routing. Authorization is accomplished via a Bearer service token in the request header. Service tokens are not tied to a specific user. Learn more about service users here: https://community.sentinelone.com/s/article/000005290. Due to limitations, clicking "Run on console" may not work as expected, and the "Body Sample" may not be accurate because of polymorphism in the body. Refer to the "Body Schema" instead. Only one set of attributes like `log` or `pq` should …

Required permissions: `Skylight Query API.view`

Parameters:
- `body` [body, object] — 

Responses: 200 Query launched successfully.

## `DELETE /sdl/v2/api/queries/{id}`
**Delete query**
`operationId`: `_sdl_v2_api_queries_{id}_delete`

Remove query from the list of launched queries. Clients are required to call this after their query is complete. Subsequent polls using specified token will return not found response. The X-Dataset-Query-Forward-Tag header value from the launch query response must be applied for routing. Authorization is accomplished via a Bearer service token in the request header. Service tokens are not tied to a specific user. Learn more about service users here: https://community.sentinelone.com/s/article/000005290. Due to limitations, clicking "Run on console" may not work as expected

Required permissions: `Skylight Query API.view`

Parameters:
- `id` [path, string] **required** — The unique query identifier
- `X-Dataset-Query-Forward-Tag` [header, string] **required** — routing header

Responses: 204 Query has been removed successfully

## `GET /sdl/v2/api/queries/{id}`
**Poll query**
`operationId`: `_sdl_v2_api_queries_{id}_get`

Poll a previously launched query by its unique identifier. Responses will return a `QueryResult`. If the query has not yet completed, the `data` field will be null. Once the query completes, `data` will contain the full result set (up to configured limits). It is recommended to poll every second; queries expire after the configured TTL (default 30 seconds). The X-Dataset-Query-Forward-Tag header value from the launch query response must be applied for routing. Authorization is accomplished via a Bearer service token in the request header. Service tokens are not tied to a specific user. Learn more about service users here: https://community.sentinelone.com/s/article/000005290. Due to limitations, clicking "Run on console" may not work as expected

Required permissions: `Skylight Query API.view`

Parameters:
- `id` [path, string] **required** — The unique query identifier
- `lastStepSeen` [query, integer] **required** — The step to start return result from
- `X-Dataset-Query-Forward-Tag` [header, string] **required** — routing header

Responses: 200 Results retrieved successfully., 404 If no launched query found for the combination of query id +
