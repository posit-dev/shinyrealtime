#' @keywords internal
"_PACKAGE"

## usethis namespace: start
## usethis namespace: end
NULL

# Setup when the package is loaded
.onLoad <- function(libname, pkgname) {
  # Register the custom message handler for realtime_send
  shiny::registerInputHandler("realtime_send", function(val, session, name) {
    val
  }, force = TRUE)
}