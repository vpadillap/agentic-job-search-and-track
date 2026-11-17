# Vendored libraries

Pinned single files; updating one is a one-file change. No CDN, no build step.

| File | Package | Version | License | Source |
|---|---|---|---|---|
| `preact-htm.js` | `htm` (`htm/preact/standalone.module.js`): htm + Preact 10 + Preact hooks in one ES module | htm 3.1.1 (built against Preact ^10.2.0) | htm: Apache-2.0 (`LICENSE-htm.txt`); Preact: MIT | https://registry.npmjs.org/htm/-/htm-3.1.1.tgz, integrity `sha512-983Vyg8NwUE7JkZ6NmOqpCZ+sh1bKv2iYTlUkzlWmA5JD2acKoxd4KVxbMmxX/85mtfdnDmTFoNKcg5DGAvxNQ==` |

Preact license (MIT): Copyright (c) 2015-present Jason Miller. Permission is
hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of
the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED.

To update: download the new `htm` tarball from the npm registry, check its
integrity hash, copy `preact/standalone.module.js` here, and update this table.
