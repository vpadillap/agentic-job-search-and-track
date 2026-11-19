# provider-throttling Specification

## Purpose
Telling a temporary throttle apart from a hard block, waiting as the site asks, cool-downs that resume the same run, and keeping progress across them.

## Requirements

### Requirement: Soft and hard blocks are told apart
Every built-in reader SHALL treat HTTP 429, LinkedIn's 999, HTTP 503 with a
`Retry-After` header, and a challenge page its provider file names as a soft
block (a throttle). It SHALL treat HTTP 403, a block page its provider file
names, a redirect to a sign-in or sign-up page, and a sign-in wall that does
not close as a hard block, which stops the provider for the rest of the run
as before.

#### Scenario: Throttle
- **WHEN** a request is answered with HTTP 429
- **THEN** the reader handles it as a soft block and does not record the provider as failed

#### Scenario: Hard block
- **WHEN** a request is answered with HTTP 403
- **THEN** the provider is recorded as blocked for the run and later calls in that run are refused

#### Scenario: 503 without Retry-After
- **WHEN** a request is answered with HTTP 503 and no `Retry-After` header
- **THEN** the provider stops for the run with reason `error`

### Requirement: Waiting as the site asks
On a soft block the reader SHALL repeat the same request only after waiting:
the `Retry-After` value when the answer has one (delta-seconds or an HTTP
date), otherwise exponential backoff with jitter, and never less than the
provider's minimum gap between requests. It SHALL make at most 3 attempts per
request, wait at most 2 minutes before any one retry, and retry at most 6
times per provider per run.

#### Scenario: Retry-After honoured
- **WHEN** a request is answered 429 with `Retry-After: 40` and the repeat succeeds
- **THEN** the repeat is sent no sooner than 40 seconds later and the reader goes on normally

#### Scenario: Backoff without Retry-After
- **WHEN** a request is answered 429 twice without `Retry-After` and then succeeds
- **THEN** the waits before the second and third attempts are between 10 and 20 seconds and between 20 and 40 seconds

#### Scenario: Run budget used up
- **WHEN** six retries were already made for the provider in this run and a request is throttled again
- **THEN** the reader does not retry it and starts a cool-down

### Requirement: Cool-down resumes the same run
When a request is still throttled after its attempts, the site asks for a
wait longer than 2 minutes, or the run's retry budget is used up, the reader
SHALL end the call, keep what it read, record a cool-down on the run's
provider entry, and report `stopped` with reason `throttled` and the time it
may resume. The cool-down SHALL last at least 15 minutes the first time and
30 minutes the second time in a run, or longer when `Retry-After` asks for
it. A call before that time SHALL be refused without any request. The first
call after it SHALL proceed in the same run. A throttle that would need a
third cool-down in the same run SHALL stop the provider for the run with
reason `blocked`. There SHALL be no way to end a cool-down early.

#### Scenario: Call during a cool-down
- **WHEN** the reader is called for another title while the provider is cooling down
- **THEN** it sends no request and answers `provider_cooling` with the time it may resume

#### Scenario: Call after the cool-down
- **WHEN** the reader is called after the cool-down's time has passed
- **THEN** it reads the title in the same run

#### Scenario: Third throttle
- **WHEN** a provider that already cooled down twice in the run is throttled past its retries again
- **THEN** it is recorded as blocked for the run and later calls are refused

#### Scenario: Run finished during a cool-down
- **WHEN** the run is finished while a provider is still cooling down
- **THEN** that provider is recorded as failed with reason `throttled` and the time it was waiting for

#### Scenario: New run during a cool-down
- **WHEN** a new run starts before an earlier run's cool-down for a provider has ended
- **THEN** the new run's entry for that provider carries the remaining cool-down

### Requirement: Progress kept across a cool-down
The reader SHALL keep, in the run's state file, which titles are complete,
which search pages of a title were read, and which postings were opened. After
a cool-down it SHALL NOT search a completed title again, SHALL NOT request a
page-addressed search page already read, and SHALL NOT open a posting already
opened in the run. A posting whose request was throttled SHALL NOT count as
opened.

#### Scenario: Resuming a title
- **WHEN** LinkedIn was throttled on the second search page of a title and the title is read again after the cool-down
- **THEN** the reader starts at the second page and opens none of the postings it opened before

#### Scenario: Throttled posting
- **WHEN** a posting's page is throttled and the reader cools down
- **THEN** that posting is opened in the first call after the cool-down

#### Scenario: Completed title
- **WHEN** the reader is called for a title it completed earlier in the run
- **THEN** it sends no request and reports the title as already done

### Requirement: Waiting is the only response to a throttle
On a soft or hard block the readers SHALL NOT use proxies, change or rotate
the user agent or other request headers, use the user's accounts or cookies,
or start a fresh browser identity to get past the block. Scrapling's own
automatic retries SHALL be off, so that every repeat request goes through
this policy.

#### Scenario: Repeat after a throttle
- **WHEN** a request is repeated after a soft block
- **THEN** it is sent with the same headers, from the same machine, without a proxy or an account
