Developer quickstart
====================

Learn how to make your first API request.

The OpenAI API provides a simple interface to state-of-the-art AI [models](/docs/models) for natural language processing, image generation, semantic search, and speech recognition. Follow this guide to learn how to generate human-like responses to [natural language prompts](/docs/guides/text-generation), [create vector embeddings](/docs/guides/embeddings) for semantic search, and [generate images](/docs/guides/images) from textual descriptions.

Create and export an API key
----------------------------

[Create an API key in the dashboard here](/api-keys), which you’ll use to securely [access the API](/docs/api-reference/authentication). Store the key in a safe location, like a [`.zshrc` file](https://www.freecodecamp.org/news/how-do-zsh-configuration-files-work/) or another text file on your computer. Once you’ve generated an API key, export it as an [environment variable](https://en.wikipedia.org/wiki/Environment_variable) in your terminal.

macOS / Linux

Export an environment variable on macOS or Linux systems

```bash
export OPENAI_API_KEY="your_api_key_here"
```

Windows

Export an environment variable in PowerShell

```bash
setx OPENAI_API_KEY "your_api_key_here"
```

Make your first API request
---------------------------

With your OpenAI API key exported as an environment variable, you're ready to make your first API request. You can either use the [REST API](/docs/api-reference) directly with the HTTP client of your choice, or use one of our [official SDKs](/docs/libraries) as shown below.

JavaScript

To use the OpenAI API in server-side JavaScript environments like Node.js, Deno, or Bun, you can use the official [OpenAI SDK for TypeScript and JavaScript](https://github.com/openai/openai-node). Get started by installing the SDK using [npm](https://www.npmjs.com/) or your preferred package manager:

Install the OpenAI SDK with npm

```bash
npm install openai
```

With the OpenAI SDK installed, create a file called `example.mjs` and copy one of the following examples into it:

Generate text

Create a human-like response to a prompt

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
        { role: "system", content: "You are a helpful assistant." },
        {
            role: "user",
            content: "Write a haiku about recursion in programming.",
        },
    ],
    store: true,
});

console.log(completion.choices[0].message);
```

Generate an image

Generate an image based on a textual prompt

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const image = await openai.images.generate({ prompt: "A cute baby sea otter" });

console.log(image.data[0].url);
```

Create vector embeddings

Create vector embeddings for a string of text

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const embedding = await openai.embeddings.create({
    model: "text-embedding-3-large",
    input: "The quick brown fox jumped over the lazy dog",
});

console.log(embedding);
```

Execute the code with `node example.mjs` (or the equivalent command for Deno or Bun). In a few moments, you should see the output of your API request!

Python

To use the OpenAI API in Python, you can use the official [OpenAI SDK for Python](https://github.com/openai/openai-python). Get started by installing the SDK using [pip](https://pypi.org/project/pip/):

Install the OpenAI SDK with pip

```bash
pip install openai
```

With the OpenAI SDK installed, create a file called `example.py` and copy one of the following examples into it:

Generate text

Create a human-like response to a prompt

```python
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)
```

Generate an image

Generate an image based on a textual prompt

```python
from openai import OpenAI
client = OpenAI()

response = client.images.generate(
    prompt="A cute baby sea otter",
    n=2,
    size="1024x1024"
)

print(response.data[0].url)
```

Create vector embeddings

Create vector embeddings for a string of text

```python
from openai import OpenAI
client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-large",
    input="The food was delicious and the waiter..."
)

print(response)
```

Execute the code with `python example.py`. In a few moments, you should see the output of your API request!

curl

On Unix-based systems, you can test out the [OpenAI REST API](/docs/api-reference) using [curl](https://curl.se/). The following commands assume that you have exported the `OPENAI_API_KEY` system environment variable as shown above.

Generate text

Create a human-like response to a prompt

```bash
curl "https://api.openai.com/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "Write a haiku that explains the concept of recursion."
            }
        ]
    }'
```

Generate an image

Generate an image based on a textual prompt

```bash
curl "https://api.openai.com/v1/images/generations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "prompt": "A cute baby sea otter",
        "n": 2,
        "size": "1024x1024"
    }'
```

Create vector embeddings

Create vector embeddings for a string of text

```bash
curl "https://api.openai.com/v1/embeddings" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{
        "input": "The food was delicious and the waiter...",
        "model": "text-embedding-3-large"
    }'
```

Execute the curl commands above in your terminal. In a few moments, you should see the output of your API request!

Next steps
----------

Now that you've made your first OpenAI API request, you can explore the following resources:

[

Chat Completions

Learn more about generating text responses to natural language prompts

](/docs/guides/text-generation)[

Image Generation

Generate images using our DALL·E model

](/docs/guides/images)[

Embeddings

Create vector representations of text, used for similarity search

](/docs/guides/embeddings)[

Text-to-speech

Generate human-like voice recordings with our text-to-speech model

](/docs/guides/text-to-speech)[

Speech-to-text

Create transcriptions of voice recordings with our Whisper model

](/docs/guides/speech-to-text)[

Moderation

Analyze and filter user-created content with our moderation model

](/docs/guides/moderation)[

Fine-tuning

Fine-tune our models with your own data

](/docs/guides/fine-tuning)[

Batch

Batch requests for async jobs

](/docs/guides/batch)[

Full API Reference

View the full REST API reference for OpenAI

](/docs/api-reference)