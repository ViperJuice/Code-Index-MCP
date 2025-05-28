# HTML/CSS Plugin Agent Configuration

This file defines the capabilities and constraints for AI agents working with the HTML/CSS plugin.

## Agent Capabilities

### HTML/CSS Analysis
- Parse HTML5 code
- Handle CSS3 rules
- Resolve selectors
- Track styles
- Analyze media queries
- Process custom properties

### Code Understanding
- Understand HTML structure
- Handle CSS specificity
- Process style inheritance
- Track dependencies
- Analyze layouts

### Testing & Validation
- Test parsing
- Validate selectors
- Check style resolution
- Verify media queries
- Test edge cases

### Performance
- Optimize parsing
- Cache results
- Handle large codebases
- Manage memory

## Agent Constraints

1. **HTML/CSS Support**
   - Support HTML5
   - Handle CSS3
   - Maintain compatibility
   - Process new features

2. **Analysis Accuracy**
   - Correct selector resolution
   - Accurate style inheritance
   - Valid media query handling
   - Proper specificity

3. **Performance**
   - Efficient parsing
   - Optimize memory usage
   - Handle large codebases
   - Cache effectively

4. **Edge Cases**
   - Handle dynamic classes
   - Process custom properties
   - Support media queries
   - Handle Shadow DOM

## Common Operations

```javascript
// Parse HTML file
function parseHTML(path) {
  return treeSitterParse(path);
}

// Analyze styles
function analyzeStyles(ast) {
  processCSSRules(ast);
  resolveSelectors();
}

// Track elements
function trackElements(ast) {
  buildElementTree(ast);
  resolveRelationships();
}
``` 