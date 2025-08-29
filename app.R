library(tidyverse)
library(shiny)
library(bslib)
library(dotenv)
library(ellmer)

source("realtime.R")

# Read prompt file
prompt <- readLines("prompt-r.md") |> paste(collapse = "\n")

# Load example datasets
samples <- list()
for (dataset in c("mpg", "diamonds", "economics", "iris", "mtcars")) {
  df <- eval(parse(text = dataset))
  if (is.data.frame(df)) {
    samples <- c(
      samples,
      paste0(
        "## ",
        dataset,
        "\n\n",
        capture.output(write.csv(head(df), "")),
        collapse = "\n"
      )
    )
  }
}

prompt <- paste0(
  prompt,
  "\n\n# Available Datasets\n\n",
  paste(samples, collapse = "\n\n")
)

ui <- page_fillable(
  style = "--bslib-spacer: 1rem; padding-bottom: 0;",
  card(
    full_screen = TRUE,
    card_header("Plot"),
    card_body(padding = 0, plotOutput("plot", fill = TRUE))
  ),
  card(
    full_screen = TRUE,
    card_header("Code"),
    verbatimTextOutput("code_text")
  ),
  realtimeUI(
    "realtime1",
    style = "z-index: 100000; margin-left: auto; margin-right: auto;",
    right = NULL
  ),
)

server <- function(input, output, session) {
  last_code <- reactiveVal()

  run_r_plot_code <- function(code) {
    beepr::beep("shutter.wav")
    last_code(code)
  }

  run_r_plot_code_tool <- ellmer::tool(
    run_r_plot_code,
    "Run R code that generates a static plot",
    arguments = list(
      code = type_string(
        "The R code to run that generates a plot. If using ggplot2, the last expression in the code should be the plot object, e.g. `p`."
      )
    )
  )

  realtime_controls <- realtimeServer(
    "realtime1",
    voice = "cedar",
    instructions = prompt,
    tools = list(run_r_plot_code_tool),
    speed = 1.1
  )

  # Show notification when the model is generating code
  observe({
    event <- realtime_controls$event()
    if (
      event$type == "conversation.item.created" &&
        event$item$type == "function_call"
    ) {
      shiny::showNotification(
        "Generating code, please wait...",
        id = event$item$id,
        closeButton = FALSE
      )
    } else if (
      event$type == "response.output_item.done" &&
        event$item$type == "function_call"
    ) {
      shiny::removeNotification(id = event$item$id)
    }
  })

  output$plot <- renderPlot({
    req(last_code())
    print("Plotting:")
    print(last_code())
    eval(parse(text = last_code()))
  })

  output$code_text <- renderText({
    req(last_code())
    last_code()
  })
}

shinyApp(ui, server)
