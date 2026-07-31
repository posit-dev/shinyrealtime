test_that("empty_obj serializes to {} not []", {
  expect_equal(as.character(jsonlite::toJSON(empty_obj())), "{}")
})

test_that("coerce_output passes through character scalars", {
  expect_equal(coerce_output("hello"), "hello")
})

test_that("coerce_output JSON-serializes named lists (preserves field names)", {
  expect_equal(
    coerce_output(list(temp = 72, cond = "sunny")),
    '{"temp":72,"cond":"sunny"}'
  )
})

test_that("coerce_output JSON-serializes data.frames as records", {
  expect_equal(
    coerce_output(data.frame(a = 1:2, b = c("x", "y"))),
    '[{"a":1,"b":"x"},{"a":2,"b":"y"}]'
  )
})

test_that("coerce_output serializes numeric scalars", {
  expect_equal(coerce_output(42), "42")
})

test_that("coerce_output returns fallback for NULL / empty / empty-string", {
  expect_equal(coerce_output(NULL), "OK")
  expect_equal(coerce_output(list()), "OK")
  expect_equal(coerce_output(""), "OK")
})

test_that("coerce_output respects custom fallback", {
  expect_equal(coerce_output(NULL, fallback = "no-op"), "no-op")
})

test_that("flatten_events handles varargs form send(e1, e2)", {
  e1 <- list(type = "a")
  e2 <- list(type = "b")
  expect_equal(flatten_events(e1, e2), list(e1, e2))
})

test_that("flatten_events unwraps backward-compat list form send(list(e1, e2))", {
  e1 <- list(type = "a")
  e2 <- list(type = "b")
  expect_equal(flatten_events(list(e1, e2)), list(e1, e2))
})

test_that("flatten_events treats a single event as a one-element list", {
  e1 <- list(type = "a")
  expect_equal(flatten_events(e1), list(e1))
})

test_that("flatten_events preserves nested content unchanged", {
  e <- list(type = "conversation.item.create", item = list(role = "user"))
  result <- flatten_events(e)
  expect_equal(length(result), 1)
  expect_equal(result[[1]]$item$role, "user")
})

test_that("send() output serializes to a flat JSON array (regression: no nested [[]])", {
  e1 <- list(type = "a")
  e2 <- list(type = "b")
  json_varargs <- as.character(jsonlite::toJSON(flatten_events(e1, e2), auto_unbox = TRUE))
  json_list <- as.character(jsonlite::toJSON(flatten_events(list(e1, e2)), auto_unbox = TRUE))
  expect_equal(json_varargs, '[{"type":"a"},{"type":"b"}]')
  expect_equal(json_list, '[{"type":"a"},{"type":"b"}]')
})
