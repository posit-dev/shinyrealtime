library(tidyverse)
library(shiny)
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

ui <- fillPage(
  realtimeUI("realtime1"),
  plotOutput("plot", fill = TRUE),
  tags$div(
    style = "height: 200px; overflow-y: auto;",
    verbatimTextOutput("code_text")
  )
)

server <- function(input, output, session) {
  last_code <- reactiveVal()

  run_r_plot_code <- function(code) {
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
    voice = "fable",
    instructions = prompt,
    tools = list(run_r_plot_code_tool),
    speed = 1.1
  )

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
