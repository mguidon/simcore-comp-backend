#include <iostream>
#include <chrono>
#include <thread>
#include <string>
#include <fstream>
#include <stdlib.h> 

int main(int argc, char const *argv[])
{
    std::string input_filename;
    std::string output_filename;

    if (argc>1)
    {
    //    input_filename = std::string(argv[1]);
    }

    if (argc>2)
    {
     //   output_filename = std::string(argv[2]);
    }

    int N = 4;
    
    if (!input_filename.empty())
    {
        std::fstream input(input_filename, std::ios_base::in);
        input >> N;
        input.close();
    }
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

    if (!output_filename.empty())
    {
        std::ofstream output;
        output.open(output_filename);
        int random_number = rand() % 8 + 1;
        output <<  random_number << std::endl;
        output.close();
    }
    return 0;
}
