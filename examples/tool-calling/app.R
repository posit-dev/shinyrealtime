library(bslib)
library(dotenv)
library(ellmer)
library(shiny)
library(shinyrealtime)

# Minimal runnable example exercising tool calls end-to-end against
# gpt-realtime-2. Two tools cover the paths that changed in PR #8:
#
#   get_weather(city) -> named list. Verifies that structured tool output
#     is JSON-serialized (was previously deparsed by as.character()).
#   list_stores(city) -> data.frame. Same, for the tabular case.
#
# Either tool raises for city = "error" so the error branch also gets
# exercised; the model should relay the actual message rather than a
# fixed sentinel.

instructions <- paste(
  "You are a concise weather assistant. When the user asks about weather,",
  "call get_weather(city). When they ask about stores in a city, call",
  "list_stores(city). Always call the tool rather than making up data.",
  "If a tool errors, tell the user exactly what the error said."
)

# --- Tool implementations ------------------------------------------------

get_weather <- function(city) {
  if (identical(tolower(city), "error")) {
    stop("Weather service is temporarily unavailable for this city.")
  }
  # Structured output — reviewer's key concern for coerce_output.
  list(
    city = city,
    temp_f = sample(40:85, 1),
    condition = sample(c("sunny", "cloudy", "rainy", "windy"), 1),
    humidity_pct = sample(20:90, 1)
  )
}

list_stores <- function(city) {
  if (identical(tolower(city), "error")) {
    stop("Store directory lookup failed.")
  }
  # data.frame output — the case that used to serialize as literal R source.
  data.frame(
    name = c("Downtown", "Airport", "Suburb"),
    address = paste(c("100 Main St,", "500 Airport Rd,", "42 Maple Ave,"), city),
    open_now = c(TRUE, TRUE, FALSE)
  )
}

get_weather_tool <- ellmer::tool(
  get_weather,
  "Get the current weather for a city. Returns a structured record.",
  arguments = list(
    city = type_string("City name, e.g. 'Boston'.")
  )
)

list_stores_tool <- ellmer::tool(
  list_stores,
  "List retail stores in a city. Returns a table of stores.",
  arguments = list(
    city = type_string("City name, e.g. 'Boston'.")
  )
)

# --- UI / Server ---------------------------------------------------------

ui <- page_sidebar(
  title = "shinyrealtime tool-calling example",
  sidebar = sidebar(
    open = "always",
    h5("Try saying:"),
    tags$ul(
      tags$li("\"What's the weather in Boston?\""),
      tags$li("\"List the stores in Chicago.\""),
      tags$li("\"Get the weather in error.\" (triggers error path)")
    ),
    hr(),
    verbatimTextOutput("last_event")
  ),
  realtime_ui("rt")
)

server <- function(input, output, session) {
  controls <- realtime_server(
    "rt",
    model = "gpt-realtime-2",
    instructions = instructions,
    tools = list(get_weather_tool, list_stores_tool),
    debug = TRUE
  )

  output$last_event <- renderPrint({
    controls$event()
  })
}

shinyApp(ui, server)
