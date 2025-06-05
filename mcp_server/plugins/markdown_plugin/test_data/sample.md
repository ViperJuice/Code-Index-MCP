---
title: "Sample Markdown Document"
author: "Test Author"
date: "2024-12-18"
tags: ["sample", "test", "markdown"]
layout: "post"
---

# Sample Markdown Document

This is a comprehensive sample Markdown document that demonstrates various features.

## Headers and Structure

### Level 3 Header
#### Level 4 Header
##### Level 5 Header
###### Level 6 Header

## Code Blocks

Here's a Python code block:

```python
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "Hello, World!"

class SampleClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"
```

JavaScript example:

```javascript {highlight: [2, 3]}
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const result = fibonacci(10);
console.log(result);
```

SQL query:

```sql
SELECT 
    users.name,
    COUNT(orders.id) as order_count
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id
ORDER BY order_count DESC;
```

## Links and References

This is a [regular link](https://example.com) to an external site.

Here's a [reference link][ref1] and another [reference][ref2].

You can also use [relative links](./other-file.md) for internal navigation.

### Reference Definitions

[ref1]: https://github.com "GitHub Homepage"
[ref2]: https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax "GitHub Markdown Guide"

## Images

![Sample Image](https://via.placeholder.com/300x200 "Placeholder Image")

![Local Image][local-img]

[local-img]: ./images/sample.png "Local Sample Image"

## Tables

| Feature | Supported | Notes |
|---------|-----------|-------|
| Headers | ✅ | All levels 1-6 |
| Code Blocks | ✅ | With syntax highlighting |
| Tables | ✅ | GitHub-flavored |
| Task Lists | ✅ | See below |
| Math | ✅ | LaTeX syntax |

### Alignment Examples

| Left Aligned | Center Aligned | Right Aligned |
|:-------------|:--------------:|--------------:|
| Item 1 | Item 2 | Item 3 |
| Long content here | Centered | 100 |
| Short | Medium content | 1,000 |

## Task Lists

- [x] Complete basic Markdown support
- [x] Add code block parsing
- [ ] Implement advanced features
  - [x] Table parsing
  - [ ] Math formula support
  - [ ] Wiki-style links
- [ ] Create comprehensive tests
- [X] Document all features

## Math Formulas

Inline math: The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

Display math:

$$
\begin{aligned}
\nabla \times \vec{\mathbf{E}} &= -\frac{\partial \mathbf{B}}{\partial t} \\
\nabla \times \vec{\mathbf{B}} &= \mu_0\vec{\mathbf{J}} + \mu_0\varepsilon_0\frac{\partial \mathbf{E}}{\partial t}
\end{aligned}
$$

Another formula:

$$E = mc^2$$

## Wiki-Style Links

You can link to other pages using [[Wiki Links]] or [[Other Page|Display Text]].

## Footnotes

This is a sentence with a footnote[^1].

Here's another footnote[^note].

[^1]: This is the first footnote.
[^note]: This is a named footnote with more detailed content that can span multiple lines.

## Blockquotes

> This is a blockquote.
> It can span multiple lines.
>
> > Nested blockquotes are also supported.

## Lists

### Unordered Lists

- Item 1
- Item 2
  - Nested item 2.1
  - Nested item 2.2
    - Double nested item
- Item 3

### Ordered Lists

1. First item
2. Second item
   1. Nested numbered item
   2. Another nested item
3. Third item

## Emphasis

*Italic text* and _also italic_.

**Bold text** and __also bold__.

***Bold and italic*** and ___also bold and italic___.

~~Strikethrough text~~.

## Horizontal Rules

---

***

___

## Code and Preformatted Text

Inline `code` can be used within sentences.

    This is a preformatted code block
    with four-space indentation.
    
    function example() {
        return "indented code";
    }

## HTML Elements

Some <em>HTML</em> tags are <strong>supported</strong>.

<details>
<summary>Click to expand</summary>

This content is hidden by default.

</details>

## Line Breaks

This line ends with two spaces.  
This creates a line break.

This paragraph has
a normal line break.

---

*This document demonstrates various Markdown features for testing purposes.*