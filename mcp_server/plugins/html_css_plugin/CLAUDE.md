# HTML/CSS Plugin

This plugin provides HTML and CSS code indexing and analysis capabilities for the MCP server.

## Features

- HTML5 parsing
- CSS3 analysis
- Selector resolution
- Style inheritance
- Media query handling
- Custom property tracking

## Implementation Details

### Parser
- Uses Tree-sitter for HTML/CSS
- Handles HTML5 elements
- Processes CSS rules
- Manages style sheets

### Indexer
- Tracks element relationships
- Maps style rules
- Records custom properties
- Maintains specificity

### Analysis
- Selector matching
- Style inheritance
- Media query analysis
- Custom property resolution

## Common Patterns

1. **Element Analysis**
   ```html
   <!-- Track element relationships -->
   <div class="container">
     <nav class="navigation">
       <!-- Elements are tracked -->
     </nav>
   </div>
   ```

2. **Style Resolution**
   ```css
   /* Analyze style rules */
   .container {
     --custom-prop: value;
     display: flex;
   }
   ```

3. **Media Query Handling**
   ```css
   /* Process media queries */
   @media (max-width: 768px) {
     .container {
       flex-direction: column;
     }
   }
   ```

## Edge Cases

- Dynamic classes
- CSS custom properties
- Media query cascades
- Style inheritance
- Shadow DOM
- CSS modules 