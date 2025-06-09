---
title: Complex Markdown Document
author: Test Author
date: 2024-01-15
tags: [markdown, documentation, testing]
version: 1.0.0
---

# Complex Markdown Document

This document showcases all major markdown features for comprehensive testing.

## Table of Contents
- [Text Formatting](#text-formatting)
- [Lists](#lists)
- [Links and Images](#links-and-images)
- [Code Blocks](#code-blocks)
- [Tables](#tables)
- [Blockquotes](#blockquotes)
- [Advanced Features](#advanced-features)

## Text Formatting

This section demonstrates various text formatting options:

- **Bold text** using double asterisks
- *Italic text* using single asterisks
- ***Bold and italic*** combined
- ~~Strikethrough text~~ using tildes
- `Inline code` using backticks
- ==Highlighted text== (if supported)

You can also use _underscores_ for *emphasis* and __double underscores__ for **strong emphasis**.

## Lists

### Unordered Lists

- First item
- Second item
  - Nested item 1
  - Nested item 2
    - Deep nested item
- Third item

* Alternative bullet style
* Works the same way
  * With nesting

### Ordered Lists

1. First step
2. Second step
   1. Sub-step A
   2. Sub-step B
3. Third step
   1. Another sub-step
   2. And another

### Task Lists

- [x] Completed task
- [ ] Incomplete task
- [x] Another completed task
  - [ ] Nested incomplete task
  - [x] Nested complete task

## Links and Images

### Links

- [External link to GitHub](https://github.com)
- [Internal link to top](#complex-markdown-document)
- [Reference-style link][reference]
- <https://www.example.com> (autolink)
- [Link with title](https://www.example.com "Example Website")

[reference]: https://www.reference-example.com "Reference Link"

### Images

![Alt text for image](https://via.placeholder.com/150 "Image title")

![Reference-style image][image-ref]

[image-ref]: https://via.placeholder.com/200x100 "Another image"

## Code Blocks

### Inline Code

Use `print("Hello, World!")` to output text in Python.

### Fenced Code Blocks

```python
def fibonacci(n):
    """Generate Fibonacci sequence up to n terms."""
    a, b = 0, 1
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result

# Example usage
print(fibonacci(10))
```

```javascript
// JavaScript example
class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(x) {
        this.result += x;
        return this;
    }
    
    multiply(x) {
        this.result *= x;
        return this;
    }
    
    getResult() {
        return this.result;
    }
}

const calc = new Calculator();
console.log(calc.add(5).multiply(3).getResult()); // 15
```

```bash
#!/bin/bash
# Bash script example

echo "System Information:"
echo "==================="
uname -a
echo ""
echo "Disk Usage:"
df -h
echo ""
echo "Memory Usage:"
free -m
```

### Code Block Without Language

```
This is a code block without syntax highlighting.
It can contain any text format.
    Including indentation
    And special characters: <>&*[]
```

## Tables

### Simple Table

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |

### Aligned Table

| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Left         | Center         | Right         |
| 123          | 456            | 789           |
| abc          | def            | ghi           |

### Complex Table

| Feature | Description | Status | Priority |
|---------|-------------|--------|----------|
| **Markdown Parser** | Parse all markdown elements | ✅ Complete | High |
| *Syntax Highlighting* | Add code syntax colors | 🚧 In Progress | Medium |
| ~~Legacy Support~~ | Support old format | ❌ Cancelled | Low |
| `API Integration` | Connect to external APIs | 📅 Planned | High |

## Blockquotes

> This is a simple blockquote. It can contain multiple sentences.
> The quote continues here.

> ## Blockquote with Header
> 
> You can include other markdown elements inside blockquotes:
> - List item 1
> - List item 2
> 
> > Nested blockquote
> > With multiple lines
> 
> Even code blocks work:
> ```python
> print("Hello from a blockquote!")
> ```

## Advanced Features

### Horizontal Rules

Three or more hyphens:

---

Three or more asterisks:

***

Three or more underscores:

___

### HTML Elements

<details>
<summary>Click to expand</summary>

This content is hidden by default and can be expanded by clicking the summary.

- It can contain any markdown
- Including lists
- And other elements

</details>

<div align="center">
  <h3>Centered Content</h3>
  <p>This paragraph is centered using HTML.</p>
</div>

### Footnotes

Here's a sentence with a footnote[^1]. And another one[^2].

[^1]: This is the first footnote.
[^2]: This is the second footnote with more content.
      It can span multiple lines.

### Mathematical Expressions

Inline math: $E = mc^2$

Block math:

$$
\frac{n!}{k!(n-k)!} = \binom{n}{k}
$$

### Emoji Support

:smile: :rocket: :computer: :book: :warning:

### Definition Lists

Term 1
: Definition 1
: Alternative definition

Term 2
: Definition 2

### Abbreviations

The HTML specification is maintained by the W3C.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium

## Conclusion

This document has demonstrated a comprehensive set of markdown features including:

1. Text formatting options
2. Various list types
3. Links and images
4. Code blocks with syntax highlighting
5. Tables with alignment
6. Blockquotes with nesting
7. Advanced features like footnotes and math

For more information about markdown, visit [CommonMark](https://commonmark.org/).