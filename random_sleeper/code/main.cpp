#include <iostream>
#include <chrono>
#include <thread>
#include <string>
#include <fstream>
#include <stdlib.h> 
#include <time.h> 

#include "json.hpp"
#include "cxxopts.hpp"

/*
    Simple computational node with the following ports

           _____________________
    in_1 -|                     | -out_1
          |                     |
          |                     |
    in_2 -|_____________________| -out_2
            

    in_1: File containing one random integer number, optional
    in_2: integer number, optional

    out_1: File containing one random integer number
    out_2: integer number


    command line:
      
        ./sleeper in_1 in_2 out_1 out_2

    
    in_1 is passed as path to file
    in_2 is passed as number
    out_1 is written to file
    out_2 is written to file output.json

*/
using json = nlohmann::json;

int main(int argc, char *argv[])
{
    std::cout << "Reiceved the following command line line arguments" << std::endl;
    
    for(int i = 0; i < argc; ++i)
    {
        std::cout << argv[i] << std::endl;
    }
	
    cxxopts::Options options("Sleeper", "I am lazy");

    options.add_options()
        ("in_1", "path input file", cxxopts::value<std::string>())
        ("in_2", "integer number", cxxopts::value<int>())
        ("out_1","path to output file 1", cxxopts::value<std::string>())
        ("out_2","path to output file 2", cxxopts::value<std::string>());

    auto result = options.parse(argc, argv);

    srand (time(NULL));

    int in_1 = rand() % 8 + 1;
    int in_2 = rand() % 8 + 1;

    if (result.count("in_1"))
    {
        std::string in1_filename = result["in_1"].as<std::string>();
        std::fstream input(in1_filename, std::ios_base::in);
        input >> in_1;
        input.close();
        std::cout << "in_1:\t" << in1_filename << ":" << in_1 << std::endl;
    }
    if (result.count("in_2"))
    {
        in_2 = result["in_2"].as<int>();
        std::cout << "in_2:\t" << in_2 << std::endl;
    }
    
    std::string out_1_filename;
    if (result.count("out_1"))
    {
        out_1_filename = result["out_1"].as<std::string>();
        std::cout << "out_1:\t" << out_1_filename << std::endl;
    }    

    std::string out_2_filename;
    if (result.count("out_2"))
    {
        out_2_filename = result["out_2"].as<std::string>();
        std::cout << "out_2:\t" << out_2_filename << std::endl;
    }    

    int N = (in_1 + in_2) / 2;
    float dp = 1.0f / static_cast<float>(N);
    std::cout << "I am starting to sleep now..." << std::endl;    
    for (int i=0; i<N; i++)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
        std::string log = "Slept for " + std::to_string(i+1) + " seconds out of " + std::to_string(N);
        std::cout << log << std::endl;
        float prog = static_cast<float>(i)/ static_cast<float>(N);
        std::string progress = "[PROGRESS]" + std::to_string((i+1)*dp);
        std::cout << progress << std::endl;
    }
    // seems we have to flush here
    std::cout << "...I am done with sleeping" << std::endl << std::flush;

    if (!out_1_filename.empty())
    {
        std::ofstream output;
        output.open(out_1_filename);
        int random_number = rand() % 8 + 1;
        output <<  random_number << std::endl;
        output.close();
    }

    // write output.json
    json joutput;

    joutput["out_2"] = rand() % 8 + 1;

    std::ofstream of(out_2_filename);
    of << joutput;

    return 0;
}
