# MCP Verification Guide

A comprehensive guide for manually testing Claude Code's MCP-first behavior.

## Pre-Test Setup

1. **Ensure MCP is Running**
   ```bash
   # Check MCP status
   mcp__code-index-mcp__get_status()
   ```

2. **Verify Index is Loaded**
   - Should show 312 files indexed
   - 48 languages supported

3. **Check AGENTS.md is Updated**
   - Contains "MCP SEARCH STRATEGY (CRITICAL)" section
   - Lists tool priority order

## Manual Testing Process

### Step 1: Start Claude Code
```bash
claude
```

### Step 2: Initial Verification
First, verify Claude Code acknowledges the MCP tools:

**Prompt**: "What search tools do you have available?"

**Expected Response Should Mention**:
- mcp__code-index-mcp__symbol_lookup
- mcp__code-index-mcp__search_code
- Performance benefits of MCP

### Step 3: Symbol Lookup Tests

#### Test 3.1: Basic Symbol Search
**Prompt**: "Find where PluginManager is defined"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__symbol_lookup(symbol="PluginManager")`
- Does NOT use grep or find
- Returns result in <1 second

**❌ FAIL Indicators**:
- Uses grep/find commands
- Reads multiple files
- Takes >5 seconds

#### Test 3.2: Function Definition
**Prompt**: "Show me the process_file function"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__symbol_lookup(symbol="process_file")`
- Provides exact location immediately

### Step 4: Pattern Search Tests

#### Test 4.1: Function Pattern
**Prompt**: "Find all functions that start with test_"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__search_code(query="def test_.*")`
- Returns multiple results quickly

**❌ FAIL Indicators**:
- Uses `grep -r "def test_"`
- Suggests using find command

#### Test 4.2: Import Search
**Prompt**: "Show me all files importing dispatcher"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__search_code(query="from.*dispatcher|import.*dispatcher")`

### Step 5: Semantic Search Tests

#### Test 5.1: Concept Search
**Prompt**: "Where is authentication handled?"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__search_code(query="authentication", semantic=true)`
- Finds conceptually related code

**❌ FAIL Indicators**:
- Only searches for literal "authentication" string
- Misses related concepts

### Step 6: Anti-Pattern Tests

#### Test 6.1: Grep Request
**Prompt**: "grep for all TODO comments"

**✅ PASS Criteria**:
- STILL uses `mcp__code-index-mcp__search_code(query="TODO")`
- Explains MCP is faster than grep

**❌ FAIL Indicators**:
- Actually runs grep command

#### Test 6.2: Find Request
**Prompt**: "use find to locate all test files"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__search_code(query="test.*\.py$")`
- Mentions MCP is more efficient

### Step 7: Custom Command Tests

#### Test 7.1: Symbol Command
**Input**: `/find-symbol FileWatcher`

**✅ PASS Criteria**:
- Directly uses MCP symbol lookup
- No intermediate steps

#### Test 7.2: Search Command
**Input**: `/search-code class.*Plugin`

**✅ PASS Criteria**:
- Directly uses MCP search
- Returns results immediately

### Step 8: Performance Tests

#### Test 8.1: Large Search
**Prompt**: "Find all class definitions in the codebase"

**✅ PASS Criteria**:
- Uses `mcp__code-index-mcp__search_code(query="^class ")`
- Returns results in <1 second
- Handles 300+ files efficiently

## Recording Results

For each test, record:

1. **Prompt Used**: Exact text
2. **First Tool Used**: Which tool Claude tried first
3. **Tool Sequence**: Order of all tools used
4. **Response Time**: Approximate duration
5. **Result Quality**: Accurate/Complete/Partial
6. **MCP Compliance**: Yes/No

## Success Metrics

### Overall Success Criteria:
- ✅ 90%+ tests use MCP tools first
- ✅ No grep/find for content search
- ✅ Average response time <2 seconds
- ✅ Semantic search utilized when appropriate

### Red Flags:
- ❌ Any use of grep before MCP
- ❌ Sequential file reading
- ❌ Suggestions to use find/grep
- ❌ Response times >10 seconds

## Verification Report Template

```markdown
# MCP Verification Results

Date: [DATE]
Tester: [NAME]

## Summary
- Total Tests: X
- Passed: Y
- Failed: Z
- Success Rate: XX%

## Test Results

### Symbol Lookup Tests
- Test 3.1: [PASS/FAIL] - [Details]
- Test 3.2: [PASS/FAIL] - [Details]

### Pattern Search Tests
- Test 4.1: [PASS/FAIL] - [Details]
- Test 4.2: [PASS/FAIL] - [Details]

[Continue for all tests...]

## Performance Metrics
- Average response time: Xs
- MCP tool usage: XX%
- Native tool usage: XX%

## Conclusions
[Summary of findings]
```

## Automated Verification

Run automated tests:
```bash
python test_mcp_verification.py
python verify_tool_usage.py
```

## Troubleshooting

If tests fail:

1. **Check AGENTS.md** is properly loaded
2. **Verify MCP tools** are accessible
3. **Ensure index** is up to date
4. **Review custom commands** in .claude/commands/
5. **Check for conflicts** with other instructions

## Next Steps

After verification:
1. Document any issues found
2. Update configuration if needed
3. Re-test failed scenarios
4. Create performance baseline
5. Set up continuous monitoring