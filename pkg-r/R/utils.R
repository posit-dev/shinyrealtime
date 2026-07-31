# Internal helpers extracted from realtime_server() so they can be unit-tested
# without spinning up a Shiny session.

# jsonlite serializes list() to [] (JSON array). To get {} (JSON object)
# we need a named-but-empty list. Realtime API rejects `response: []`.
empty_obj <- function() setNames(list(), character(0))

# Coerce tool result to non-empty scalar string. Realtime API spec wants
# `output` to be a plain string; character scalars pass through unchanged,
# everything else is JSON-serialized so lists / data.frames arrive as
# structured data rather than R's deparsed form.
coerce_output <- function(x, fallback = "OK") {
  if (is.null(x)) return(fallback)
  if (length(x) == 0) return(fallback)
  s <- tryCatch(
    if (is.character(x) && length(x) == 1) x else as.character(toJSON(x, auto_unbox = TRUE)),
    error = function(e) NULL
  )
  if (is.null(s)) return(fallback)
  if (!nzchar(s)) return(fallback)
  s
}

# Normalize send() arguments to a flat list of event objects. Accepts either
# the preferred varargs form send(e1, e2) or the backward-compatible list
# form send(list(e1, e2)). A single named list is treated as one event.
flatten_events <- function(...) {
  args <- list(...)
  if (length(args) == 1 && is.list(args[[1]]) && is.null(names(args[[1]]))) {
    args[[1]]
  } else {
    args
  }
}
