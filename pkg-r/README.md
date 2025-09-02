# shinyrealtime

An R package for integrating OpenAI's Real-Time API with Shiny applications.

## Installation

You can install the development version of shinyrealtime from GitHub:

```r
# install.packages("remotes")
remotes::install_github("jcheng5/shinyrealtime/pkg-r")
```

## Usage

```r
library(shiny)
library(shinyrealtime)

ui <- fluidPage(
  titlePanel("Realtime API Demo"),
  
  realtime_ui(
    "realtime",
    verbatimTextOutput("output")
  )
)

server <- function(input, output, session) {
  rt <- realtime_server(
    "realtime",
    model = "gpt-realtime",
    instructions = "You are a helpful assistant."
  )
  
  # Listen for response text events
  rt$on("response.text.content", function(event) {
    output$output <- renderText({
      event$text
    })
  })
}

shinyApp(ui, server)
```

## License

MIT