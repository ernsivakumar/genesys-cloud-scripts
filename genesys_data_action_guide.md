# Genesys Cloud Data Action Configuration Guide

## Overview
This guide covers the three components of Response Configuration in Genesys Cloud Data Actions:
1. **Translation Map** - Extracts data using JSONPath
2. **Translation Map Defaults** - Provides fallback values
3. **Success Template** - Formats output using Apache VTL

---

## 1. Translation Map (JSONPath)

**Purpose:** Extract specific values from raw API JSON responses

**Syntax:**
```json
{
  "aliasName": "$.json.path.expression"
}
```

### Common JSONPath Patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| `$.property` | Root level property | `$.customerId` |
| `$.object.property` | Nested property | `$.account.balance` |
| `$.array[0]` | First array element | `$.items[0].name` |
| `$.array[*]` | All array elements | `$.orders[*].id` |
| `$..property` | Recursive search | `$..email` |
| `$.array[?(@.field=='value')]` | Filtered array | `$.users[?(@.role=='admin')]` |
| `$.array[?(@.price > 100)]` | Numeric filter | `$.products[?(@.price > 100)]` |

### Example Translation Map:
```json
{
  "customerId": "$.customer.id",
  "customerName": "$.customer.fullName",
  "accountBalance": "$.account.balances[0].amount",
  "isActive": "$.customer.status",
  "orderCount": "$.orders.length()",
  "firstOrderId": "$.orders[0].orderId",
  "vipStatus": "$.customer.tier"
}
```

---

## 2. Translation Map Defaults

**Purpose:** Provide fallback values when JSONPath fails to find data (prevents flow failures)

**Important:** Null values do NOT fall back to defaults - only missing/undefined values do

### String vs Number Defaults:

**For String Values (MUST include escaped quotes):**
```json
{
  "customerName": "\"Unknown User\"",
  "customerId": "\"UNKNOWN\"",
  "email": "\"no-email@example.com\""
}
```

**For Number Values (No quotes needed):**
```json
{
  "accountBalance": "0.00",
  "orderCount": "0",
  "userAge": "18"
}
```

**For Boolean Values:**
```json
{
  "isActive": "false",
  "isVIP": "true"
}
```

---

## 3. Success Template (Apache Velocity Template Language - VTL)

**Purpose:** Format extracted data into final JSON output matching your Output Contract

### CRITICAL RULE:
**Field names in Success Template MUST exactly match your Output Contract field names!**

### Two Approaches for String Values:

#### Approach 1: Using Quoted Defaults (Recommended)
When Translation Map Defaults include escaped quotes (`"\"value\""`):

```json
{
  "translationMap": {
    "userName": "$[0].name",
    "userUsername": "$[0].username",
    "userEmail": "$[0].email"
  },
  "translationMapDefaults": {
    "userName": "\"Unknown User\"",
    "userUsername": "\"unknown\"",
    "userEmail": "\"no-email@example.com\""
  },
  "successTemplate": "{ \"userName\": ${userName}, \"userUserName\": ${userUsername}, \"userEmail\": ${userEmail} }"
}
```

**Key Points:**
- Defaults contain escaped quotes: `"\"Unknown User\"`
- Success Template uses `${variable}` WITHOUT quotes around it
- The variable value already includes quotes from the default

#### Approach 2: Using $esc.jsonEncode()
When NOT using quoted defaults:

```json
{
  "translationMap": {
    "userName": "$[0].name"
  },
  "translationMapDefaults": {
    "userName": "Unknown User"
  },
  "successTemplate": "{ \"userName\": $esc.jsonEncode(${userName}) }"
}
```

**Key Points:**
- Defaults contain raw values without quotes
- Success Template uses `$esc.jsonEncode(${variable})`
- The macro adds quotes and escapes special characters automatically

### Common VTL Directives:

**Setting Variables:**
```vtl
#set( $isVIP = $vipStatus == "VIP" )
#set( $displayName = $customerName + " (" + $customerId + ")" )
#set( $balanceNum = $accountBalance + 0 )
```

**Conditionals:**
```vtl
#if( $isActive == "true" )
  "status": "Active"
#else
  "status": "Inactive"
#end

#if( $accountBalance > 1000 )
  "tier": "Gold"
#elseif( $accountBalance > 500 )
  "tier": "Silver"
#else
  "tier": "Bronze"
#end
```

**Loops:**
```vtl
"orders": [
#foreach( $order in $ordersList )
  {
    "id": ${order.id},
    "amount": ${order.amount}
  }#if( $foreach.hasNext ),#end
#end
]
```

---

## Complete Working Example

### Input JSON (API Response):
```json
[
  {
    "id": 1,
    "name": "Leanne Graham",
    "username": "Bret",
    "email": "Sincere@april.biz"
  },
  {
    "id": 2,
    "name": "Ervin Howell",
    "username": "Antonette",
    "email": "Shanna@melissa.tv"
  }
]
```

### Output Contract Fields:
- userName
- userUserName
- userEmail

### Translation Map:
```json
{
  "userName": "$[0].name",
  "userUsername": "$[0].username",
  "userEmail": "$[0].email"
}
```

### Translation Map Defaults:
```json
{
  "userName": "\"Unknown User\"",
  "userUsername": "\"unknown\"",
  "userEmail": "\"no-email@example.com\""
}
```

### Success Template:
```vtl
{ "userName": ${userName}, "userUserName": ${userUsername}, "userEmail": ${userEmail} }
```

### Output:
```json
{
  "userName": "Leanne Graham",
  "userUserName": "Bret",
  "userEmail": "Sincere@april.biz"
}
```

---

## Common Errors & Solutions

### Error: "Expected ',' or '}' after property value in JSON"
**Cause:** Missing escaped quotes in Success Template
**Solution:** Use `"\"key\": ${variable}` pattern (not `"\"key\": \"${variable}\"`)

### Error: "Unexpected character '\' (code 92)"
**Cause:** $esc.jsonEncode() outputting escaped quotes
**Solution:** Either:
1. Remove $esc.jsonEncode() and use quoted defaults with ${variable}
2. OR keep $esc.jsonEncode() but don't wrap in additional quotes

### Error: Empty output values (Action runs but fields are blank)
**Cause:** Success Template field names don't match Output Contract field names
**Solution:** Ensure exact match between template field names and contract field names

### Error: "Transform failed to process result using 'successTemplate'"
**Cause:** Invalid JSON structure in template
**Solution:** 
1. Use single line format for simple templates
2. Ensure all quotes are properly escaped
3. Test JSON validity before deployment

---

## Best Practices

1. **Match Output Contract Names Exactly** - Success Template field names must match Output Contract field names

2. **Use Quoted Defaults for Strings** - Include escaped quotes in defaults: `"\"Default Value\"`

3. **Single Line Templates** - For simple outputs, use single line format to avoid formatting errors

4. **Test Incrementally** - 
   - First get Translation Map working (check raw response)
   - Then add Defaults
   - Finally add Success Template

5. **Verify Field Names** - Double-check that your template outputs match your Output Contract schema

6. **Handle Arrays Correctly** - Use `$[0].field` for first item, `$[*].field` for all items

7. **Use Proper Escaping** - Remember: `"` in JSON template = `\"`

---

## Quick Reference: Common Patterns

| Scenario | JSONPath |
|----------|----------|
| Get first item | `$.array[0]` or `$[0].field` |
| Get last item | `$.array[-1]` |
| Get all items | `$.array[*]` |
| Filter by value | `$.array[?(@.field=='value')]` |
| Filter by number | `$.array[?(@.price > 100)]` |
| Deep search | `$..fieldName` |
| Nested property | `$.parent.child.property` |
| Array length | `$.array.length()` |

### String Handling Decision Tree:

```
Need to output string value?
│
├─ Are you using $esc.jsonEncode()?
│  ├─ YES → Use: $esc.jsonEncode(${variable})
│  │        Defaults: "default value" (no extra quotes)
│  │
│  └─ NO  → Use: ${variable}
│           Defaults: "\"default value\"" (with escaped quotes)
│
└─ Numeric/Boolean value?
   → Use: ${variable}
      Defaults: "123" or "true" (no quotes needed)
```

---

## How to Use This Guide

When providing a JSON response for Genesys Cloud Data Action configuration:

1. **Share the JSON response** from your API
2. **Specify what fields you need** extracted
3. **Define your Output Contract** field names
4. **I will provide**:
   - Translation Map with JSONPath expressions
   - Translation Map Defaults (with proper quoting)
   - Success Template with VTL formatting
   - Explanation of each component

Save this file locally and reference it when starting new sessions!
