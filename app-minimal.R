library(shiny)
library(bslib)
library(dotenv)
library(ellmer)

source("realtime.R")

ui <- page_fluid(
  realtimeUI("realtime1")
)

server <- function(input, output, session) {
  realtimeServer("realtime1")
}

shinyApp(ui, server)
