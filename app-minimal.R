library(bslib)
library(dotenv)
library(ellmer)
library(shiny)
library(shinyrealtime)

source("realtime.R")

ui <- page_fluid(
  realtime_ui("realtime1")
)

server <- function(input, output, session) {
  realtime_server("realtime1")
}

shinyApp(ui, server)
